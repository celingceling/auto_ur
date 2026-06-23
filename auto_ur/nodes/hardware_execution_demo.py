"""Supervised opt-in arm-only hardware execution demo node."""

from types import SimpleNamespace
from typing import Any

from auto_ur import primitives as prims
from auto_ur.config import ConfigLoader
from auto_ur.primitives.execution import UR_ARM_JOINT_NAMES
from auto_ur.primitives.execution import _joint_trajectory_from


def main() -> None:
    """Plan one conservative named pose and optionally execute it."""
    import rclpy
    from control_msgs.action import FollowJointTrajectory
    from moveit.core.robot_state import RobotState  # noqa: F401
    from moveit.planning import MoveItPy
    from rclpy.action import ActionClient
    from rclpy.node import Node

    rclpy.init()
    node = Node('auto_ur_hardware_execution_demo')
    _declare_parameters(node)

    try:
        loader = ConfigLoader()
        robot_name = node.get_parameter('robot_name').value
        pose_name = node.get_parameter('pose_name').value
        safety_config_name = node.get_parameter('safety_config').value
        controller_name = node.get_parameter('controller_name').value
        action_topic = node.get_parameter('action_topic').value
        allow_execution = bool(
            node.get_parameter('allow_hardware_execution').value,
        )

        robot_config = _load_robot_config(loader, robot_name, node)
        safety_config = loader.load_safety(safety_config_name)
        safety_config['safety']['allow_hardware_execution'] = allow_execution
        robot = robot_config['robot']
        joint_state_robot_name = robot.get('name', robot_name)
        planning_group = robot.get('planning_group', 'ur_manipulator')
        expected_joints = robot.get(
            'joint_names',
            list(UR_ARM_JOINT_NAMES),
        )

        node.get_logger().warn(
            'Hardware execution demo is arm-only and supervised. '
            f'allow_hardware_execution={allow_execution}'
        )

        moveit = MoveItPy(node_name='auto_ur_hardware_execution_demo')
        moveit_context = SimpleNamespace(planning_group=planning_group)
        arm = moveit.get_planning_component(planning_group)
        robot_model = moveit.get_robot_model()
        plan_result = prims.move_to_named_pose(
            moveit_context,
            arm,
            robot_model,
            loader,
            pose_name,
            robot_name=joint_state_robot_name,
        )
        _log_plan_result(node, plan_result, controller_name, safety_config)
        if not plan_result.success:
            node.get_logger().error(plan_result.message)
            return

        client = _FollowJointTrajectoryClient(
            node,
            ActionClient,
            FollowJointTrajectory,
            action_topic,
        )
        execution_result = prims.execute_planned_trajectory(
            plan_result,
            client,
            safety_config,
            expected_joint_names=expected_joints,
            controller_name=controller_name,
        )
        if execution_result.success:
            node.get_logger().info(execution_result.message)
        else:
            node.get_logger().error(execution_result.message)
    finally:
        node.destroy_node()
        rclpy.shutdown()


class _FollowJointTrajectoryClient:
    """Small adapter around the UR driver's FollowJointTrajectory action."""

    def __init__(
        self,
        node: Any,
        action_client_type: Any,
        action_type: Any,
        action_topic: str,
    ):
        """Create the action client adapter."""
        self._node = node
        self._action_type = action_type
        self._client = action_client_type(node, action_type, action_topic)
        self._action_topic = action_topic

    def send_goal(self, joint_trajectory: Any,
                  timeout_s: float = 30.0) -> Any:
        """Send one trajectory goal and wait for the result."""
        if not self._client.wait_for_server(timeout_sec=timeout_s):
            return SimpleNamespace(
                success=False,
                message=(
                    'FollowJointTrajectory action server unavailable: '
                    f'{self._action_topic}'
                ),
            )

        goal = self._action_type.Goal()
        goal.trajectory = joint_trajectory
        send_future = self._client.send_goal_async(goal)
        if not _spin_until_done(self._node, send_future, timeout_s):
            return SimpleNamespace(
                success=False,
                message='Timed out while sending trajectory goal',
            )

        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return SimpleNamespace(
                success=False,
                message='Trajectory goal was rejected by the controller',
            )

        result_future = goal_handle.get_result_async()
        if not _spin_until_done(self._node, result_future, timeout_s):
            return SimpleNamespace(
                success=False,
                message='Timed out waiting for trajectory execution result',
            )

        action_result = result_future.result()
        result = getattr(action_result, 'result', None)
        error_code = getattr(result, 'error_code', 0)
        return SimpleNamespace(
            success=error_code == 0,
            message=(
                'Trajectory execution completed'
                if error_code == 0
                else f'Trajectory execution failed with code {error_code}'
            ),
            result=result,
        )


def _declare_parameters(node: Any) -> None:
    """Declare launch-provided parameters."""
    node.declare_parameter('robot_name', 'ur10e')
    node.declare_parameter('pose_name', 'ready')
    node.declare_parameter('safety_config', 'supervised_hardware_motion_limits')
    node.declare_parameter(
        'controller_name',
        'scaled_joint_trajectory_controller',
    )
    node.declare_parameter(
        'action_topic',
        '/scaled_joint_trajectory_controller/follow_joint_trajectory',
    )
    node.declare_parameter('allow_hardware_execution', False)


def _load_robot_config(loader: ConfigLoader, robot_name: str,
                       node: Any) -> dict[str, Any]:
    """Load a robot config, falling back to UR10e standard joints if needed."""
    try:
        return loader.load_robot(robot_name)
    except FileNotFoundError:
        node.get_logger().warn(
            f'No robot config found for {robot_name}; using ur10e defaults. '
            'Add config/robots/<robot_name>.yaml for model-specific metadata.'
        )
        return loader.load_robot('ur10e')


def _log_plan_result(node: Any, result: Any, controller_name: str,
                     safety_config: dict[str, Any]) -> None:
    """Log the trajectory details that matter before hardware execution."""
    trajectory = result.details.get('trajectory')
    joint_trajectory = _joint_trajectory_from(trajectory)
    joint_names = getattr(joint_trajectory, 'joint_names', []) or []
    points = getattr(joint_trajectory, 'points', []) or []
    safety = safety_config.get('safety', {})
    node.get_logger().warn(
        'Planned hardware trajectory summary: '
        f'controller={controller_name}, '
        f'joints={list(joint_names)}, '
        f'points={len(points)}, '
        f'velocity_scale={safety.get("max_velocity_scale")}, '
        f'acceleration_scale={safety.get("max_acceleration_scale")}'
    )
    if points:
        node.get_logger().info(f'First waypoint: {points[0]}')
        node.get_logger().info(f'Last waypoint: {points[-1]}')


def _spin_until_done(node: Any, future: Any, timeout_s: float) -> bool:
    """Spin a node until a future completes or a timeout expires."""
    import rclpy

    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_s)
    return bool(future.done())


if __name__ == '__main__':
    main()

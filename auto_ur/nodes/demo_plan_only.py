"""MoveItPy plan-only UR10e demo node."""

import time
from types import SimpleNamespace
from typing import Any

from auto_ur import primitives as prims
from auto_ur.config import ConfigLoader
from auto_ur.registry.default_actions import build_default_registry
from auto_ur.skills import pick_and_place_demo


def main() -> None:
    """Run the UR10e plan-only MoveItPy demo."""
    import rclpy
    from moveit.core.robot_state import RobotState  # noqa: F401
    from moveit.planning import MoveItPy
    from rclpy.node import Node
    from rclpy.logging import get_logger
    from trajectory_msgs.msg import JointTrajectory

    rclpy.init()
    logger = get_logger('auto_ur_demo_plan_only')
    publisher_node = Node('auto_ur_demo_trajectory_publisher')
    trajectory_publisher = publisher_node.create_publisher(
        JointTrajectory,
        'auto_ur/planned_joint_trajectory',
        10,
    )

    try:
        time.sleep(0.5)
        loader = ConfigLoader()
        robot_config = loader.load_robot('ur10e')
        demo_config = loader.load_demo('ur10e_plan_only_demo')
        robot = robot_config['robot']
        demo = demo_config['demo']
        planning_group = robot.get('planning_group', 'ur_manipulator')
        tool_frame = robot.get('tool_frame', 'tool0')

        moveit = MoveItPy(node_name='auto_ur_demo_plan_only')
        moveit_context = SimpleNamespace(planning_group=planning_group)
        arm = moveit.get_planning_component(planning_group)
        robot_model = moveit.get_robot_model()
        reg = build_default_registry()

        logger.info('Registered actions: ' + ', '.join(reg.names()))
        for result in _run_sequence(
            demo.get('sequence', []),
            moveit_context,
            arm,
            robot_model,
            loader,
            tool_frame,
        ):
            action_name = result.data.get('action_name')
            logger.info(
                f'{action_name}: '
                f'{result.success} - {result.message}'
            )
            _publish_result_trajectories(result, trajectory_publisher, logger)
            rclpy.spin_once(publisher_node, timeout_sec=0.0)
            time.sleep(0.25)
    finally:
        publisher_node.destroy_node()
        rclpy.shutdown()


def _publish_result_trajectories(result: Any, publisher: Any,
                                 logger: Any) -> None:
    """Publish successful plan result trajectories for RViz playback."""
    for label, trajectory in _trajectories_from_result(result):
        trajectory_msg = _as_robot_trajectory_msg(trajectory)
        joint_trajectory = getattr(trajectory_msg, 'joint_trajectory', None)
        if joint_trajectory is None:
            continue
        if not joint_trajectory.joint_names or not joint_trajectory.points:
            continue
        joint_trajectory.header.frame_id = label
        publisher.publish(joint_trajectory)
        logger.info(
            'Published trajectory for RViz playback: '
            f'{label} ({len(joint_trajectory.points)} points)'
        )


def _as_robot_trajectory_msg(trajectory: Any) -> Any:
    """Convert a MoveItPy RobotTrajectory wrapper to a ROS message if needed."""
    if hasattr(trajectory, 'get_robot_trajectory_msg'):
        return trajectory.get_robot_trajectory_msg()
    return trajectory


def _trajectories_from_result(result: Any) -> list[tuple[str, Any]]:
    """Return all RobotTrajectory-like objects contained in an ActionResult."""
    trajectories = []
    action_name = result.data.get('action_name', 'demo_segment')
    trajectory = result.data.get('trajectory')
    if trajectory is not None:
        label = _label_for_result(result)
        trajectories.append((label, trajectory))
    for summary in result.data.get('segment_summaries', []):
        trajectory = summary.get('trajectory')
        if trajectory is not None:
            pose_name = summary.get('pose_name', 'segment')
            trajectories.append((f'{action_name}:{pose_name}', trajectory))
    return trajectories


def _label_for_result(result: Any) -> str:
    """Build a readable label for one planned demo trajectory."""
    action_name = result.data.get('action_name', 'demo_segment')
    for key in ('pose_name', 'joint_state_name'):
        value = result.data.get(key)
        if value:
            return f'{action_name}:{value}'
    return action_name


def _run_sequence(sequence: list[dict[str, Any]], moveit: Any, arm: Any,
                  robot_model: Any, loader: ConfigLoader,
                  tool_frame: str) -> list[Any]:
    """Run the configured plan-only demo sequence."""
    results = []
    joint_states = loader.load_named_joint_states('ur10e').get(
        'named_joint_states',
        {},
    )
    cartesian_poses = loader.load_named_cartesian_poses().get(
        'named_cartesian_poses',
        {},
    )
    planning_group = getattr(moveit, 'planning_group', 'ur_manipulator')
    planned_start_state = None

    for step in sequence:
        action = step.get('action')
        if action == 'move_to_named_pose':
            result = prims.move_to_named_pose(
                moveit,
                arm,
                robot_model,
                loader,
                step['pose_name'],
                start_state=planned_start_state,
            )
            result.data.setdefault('pose_name', step['pose_name'])
        elif action == 'move_to_joint_state':
            result = prims.move_to_joint_state(
                moveit,
                arm,
                robot_model,
                joint_states[step['joint_state_name']],
                start_state=planned_start_state,
            )
            result.data.setdefault(
                'joint_state_name',
                step['joint_state_name'],
            )
        elif action == 'move_to_pose':
            result = prims.move_to_pose(
                arm,
                cartesian_poses[step['pose_name']],
                tool_frame,
                start_state=planned_start_state,
            )
            result.data.setdefault('action_name', 'move_to_pose')
            result.data.setdefault('pose_name', step['pose_name'])
        elif action == 'pick_and_place_demo':
            result = pick_and_place_demo(
                arm,
                loader,
                step.get('pick_pose_name', 'pick'),
                step.get('place_pose_name', 'place'),
                tool_frame,
                robot_model=robot_model,
                planning_group=planning_group,
                start_state=planned_start_state,
            )
        else:
            raise ValueError(f'Unknown demo action: {action}')
        results.append(result)
        if result.success:
            planned_start_state = _end_state_from_result(
                result,
                robot_model,
                planning_group,
            )
    return results


def _end_state_from_result(result: Any, robot_model: Any,
                           planning_group: str) -> Any:
    """Return the planned final RobotState from an action result."""
    end_state = result.data.get('end_state')
    if end_state is not None:
        return end_state

    trajectory = result.data.get('trajectory')
    if trajectory is not None:
        return prims.planned_state_from_trajectory(
            robot_model,
            planning_group,
            trajectory,
        )
    return None


if __name__ == '__main__':
    main()

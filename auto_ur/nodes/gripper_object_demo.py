"""Standalone UR10e Robotiq gripper plan-only demo node."""

import time
from types import SimpleNamespace
from typing import Any

from auto_ur.config import ConfigLoader
from auto_ur.skills import gripper_object_demo


def main() -> None:
    """Run the standalone gripper visual planning demo."""
    import rclpy
    from moveit.core.robot_state import RobotState  # noqa: F401
    from moveit.planning import MoveItPy
    from rclpy.logging import get_logger
    from rclpy.node import Node
    from trajectory_msgs.msg import JointTrajectory

    rclpy.init()
    logger = get_logger('auto_ur_gripper_object_demo')
    publisher_node = Node('auto_ur_gripper_object_trajectory_publisher')
    trajectory_publisher = publisher_node.create_publisher(
        JointTrajectory,
        '/auto_ur/gripper_object/planned_joint_trajectory',
        10,
    )

    try:
        time.sleep(0.5)
        loader = ConfigLoader()
        robot_config = loader.load_robot('ur10e')
        robot = robot_config['robot']
        planning_group = robot.get('planning_group', 'ur_manipulator')
        tool_frame = robot.get('tool_frame', 'tool0')

        moveit = MoveItPy(node_name='auto_ur_gripper_object_demo')
        moveit_context = SimpleNamespace(planning_group=planning_group)
        arm = moveit.get_planning_component(planning_group)
        robot_model = moveit.get_robot_model()

        result = gripper_object_demo(
            arm,
            loader,
            tool_frame,
            robot_model=robot_model,
            planning_group=getattr(
                moveit_context,
                'planning_group',
                'ur_manipulator',
            ),
        )
        logger.info(
            f"gripper_object_demo: {result.success} - {result.message}"
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
    action_name = result.data.get('action_name', 'gripper_object_demo')
    for summary in result.data.get('segment_summaries', []):
        trajectory = summary.get('trajectory')
        if trajectory is None:
            continue
        trajectory_msg = _as_robot_trajectory_msg(trajectory)
        joint_trajectory = getattr(trajectory_msg, 'joint_trajectory', None)
        if joint_trajectory is None:
            continue
        if not joint_trajectory.joint_names or not joint_trajectory.points:
            continue
        pose_name = summary.get('pose_name', 'segment')
        label = f'{action_name}:{pose_name}'
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


if __name__ == '__main__':
    main()

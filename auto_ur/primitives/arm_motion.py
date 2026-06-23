"""Direct MoveItPy primitive planning functions for the UR10e arm."""

from types import SimpleNamespace
from typing import Any

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import PrimitiveResult


def move_to_named_pose(moveit: Any, arm: Any, robot_model: Any,
                       config_loader: Any, pose_name: str,
                       start_state: Any = None,
                       robot_name: str = 'ur10e') -> PrimitiveResult:
    """Plan to a named UR joint state."""
    joint_states = config_loader.load_named_joint_states(robot_name)
    named_states = joint_states.get('named_joint_states', {})
    joint_positions = named_states.get(pose_name)
    if joint_positions is None:
        return PrimitiveResult(
            success=False,
            message=f'Unknown named joint state: {pose_name}',
            error_code=FailureType.POSE_UNKNOWN,
            failure=Failure(
                FailureType.POSE_UNKNOWN,
                f'Unknown named joint state: {pose_name}',
                {'pose_name': pose_name},
            ),
            details={
                'action_name': 'move_to_named_pose',
                'pose_name': pose_name,
            },
        )

    result = move_to_joint_state(
        moveit,
        arm,
        robot_model,
        joint_positions,
        start_state=start_state,
    )
    result.data.update({
        'action_name': 'move_to_named_pose',
        'pose_name': pose_name,
    })
    return result


def move_to_joint_state(moveit: Any, arm: Any, robot_model: Any,
                        joint_positions: dict[str, float],
                        start_state: Any = None) -> PrimitiveResult:
    """Plan to explicit joint positions without executing the trajectory."""
    try:
        planning_group = _planning_group_from(moveit)
        _set_start_state(arm, start_state)
        constraints = _make_joint_constraints(
            robot_model,
            joint_positions,
            planning_group,
        )
        if constraints is None:
            arm.set_goal_state(robot_state=joint_positions)
        else:
            arm.set_goal_state(motion_plan_constraints=[constraints])

        plan_result = arm.plan()
        return _plan_result(
            action_name='move_to_joint_state',
            plan_result=plan_result,
            extra_data={'joint_positions': joint_positions},
        )
    except Exception as exc:
        return PrimitiveResult(
            success=False,
            message=f'move_to_joint_state failed: {exc}',
            error_code=FailureType.UNKNOWN_FAILURE,
            failure=Failure(
                FailureType.UNKNOWN_FAILURE,
                f'move_to_joint_state failed: {exc}',
                {'joint_positions': joint_positions},
            ),
            details={
                'action_name': 'move_to_joint_state',
                'joint_positions': joint_positions,
            },
        )


def move_to_pose(arm: Any, pose: Any, tool_frame: str,
                 start_state: Any = None) -> PrimitiveResult:
    """Plan to a task-space end-effector pose without execution."""
    try:
        pose_msg = _as_pose_stamped(pose)
        _set_start_state(arm, start_state)
        arm.set_goal_state(pose_stamped_msg=pose_msg, pose_link=tool_frame)
        plan_result = arm.plan()
        return _plan_result(
            action_name='move_to_pose',
            plan_result=plan_result,
            extra_data={'pose': pose, 'tool_frame': tool_frame},
        )
    except Exception as exc:
        return PrimitiveResult(
            success=False,
            message=f'move_to_pose failed: {exc}',
            error_code=FailureType.UNKNOWN_FAILURE,
            failure=Failure(
                FailureType.UNKNOWN_FAILURE,
                f'move_to_pose failed: {exc}',
                {'pose': pose, 'tool_frame': tool_frame},
            ),
            details={
                'action_name': 'move_to_pose',
                'pose': pose,
                'tool_frame': tool_frame,
            },
        )


def _planning_group_from(moveit: Any) -> str:
    """Return the configured planning group name from MoveItPy-like objects."""
    return getattr(moveit, 'planning_group', 'ur_manipulator')


def _set_start_state(arm: Any, start_state: Any = None) -> None:
    """Set a supplied planned start state, or use the live current state."""
    if start_state is None:
        arm.set_start_state_to_current_state()
        return

    try:
        arm.set_start_state(robot_state=start_state)
    except TypeError:
        arm.set_start_state(start_state)


def _make_joint_constraints(robot_model: Any,
                            joint_positions: dict[str, float],
                            planning_group: str) -> Any | None:
    """Build MoveIt joint constraints when a real robot model is available."""
    if robot_model is None:
        return None

    try:
        from moveit.core.kinematic_constraints import (
            construct_joint_constraint,
        )
        from moveit.core.robot_state import RobotState
    except Exception:
        return None

    robot_state = RobotState(robot_model)
    robot_state.joint_positions = joint_positions
    joint_model_group = robot_model.get_joint_model_group(planning_group)
    return construct_joint_constraint(
        robot_state=robot_state,
        joint_model_group=joint_model_group,
    )


def _as_pose_stamped(pose: Any) -> Any:
    """Convert a pose mapping, or return PoseStamped-like input."""
    if hasattr(pose, 'header') and hasattr(pose, 'pose'):
        return pose

    try:
        from geometry_msgs.msg import PoseStamped

        pose_msg = PoseStamped()
    except Exception:
        pose_msg = SimpleNamespace(
            header=SimpleNamespace(frame_id='base_link'),
            pose=SimpleNamespace(
                position=SimpleNamespace(x=0.0, y=0.0, z=0.0),
                orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
            ),
        )

    pose_msg.header.frame_id = pose.get('frame_id', 'base_link')
    position = pose.get('position', {})
    orientation = pose.get('orientation', {})

    pose_msg.pose.position.x = float(position.get('x', 0.0))
    pose_msg.pose.position.y = float(position.get('y', 0.0))
    pose_msg.pose.position.z = float(position.get('z', 0.0))
    pose_msg.pose.orientation.x = float(orientation.get('x', 0.0))
    pose_msg.pose.orientation.y = float(orientation.get('y', 0.0))
    pose_msg.pose.orientation.z = float(orientation.get('z', 0.0))
    pose_msg.pose.orientation.w = float(orientation.get('w', 1.0))
    return pose_msg


def _plan_result(action_name: str, plan_result: Any,
                 extra_data: dict[str, Any]) -> PrimitiveResult:
    """Wrap a MoveItPy plan result in a structured primitive result."""
    success = bool(plan_result)
    trajectory = getattr(plan_result, 'trajectory', None)
    message = 'Planning succeeded' if success else 'Planning failed'
    details = {
        'action_name': action_name,
        'plan_result': plan_result,
        'trajectory': trajectory,
    }
    details.update(extra_data)
    failure = None
    if not success:
        failure = Failure(
            FailureType.PATH_BLOCKED,
            f'{action_name} planning failed',
            details,
        )
    return PrimitiveResult(
        success=success,
        message=message,
        error_code=failure.failure_type if failure else None,
        failure=failure,
        details=details,
    )


def planned_state_from_trajectory(robot_model: Any, planning_group: str,
                                  trajectory: Any) -> Any | None:
    """Build a RobotState from the final waypoint of a planned trajectory."""
    if robot_model is None or trajectory is None:
        return None

    trajectory_msg = _as_robot_trajectory_msg(trajectory)
    joint_trajectory = getattr(trajectory_msg, 'joint_trajectory', None)
    if joint_trajectory is None:
        return None
    if not joint_trajectory.joint_names or not joint_trajectory.points:
        return None

    final_point = joint_trajectory.points[-1]
    try:
        from moveit.core.robot_state import RobotState
    except Exception:
        return None

    robot_state = RobotState(robot_model)
    positions = [
        float(position)
        for position in final_point.positions
    ]
    try:
        joint_model_group = robot_model.get_joint_model_group(planning_group)
        robot_state.set_joint_group_positions(joint_model_group, positions)
    except TypeError:
        robot_state.set_joint_group_positions(planning_group, positions)
    if hasattr(robot_state, 'update'):
        robot_state.update()
    return robot_state


def _as_robot_trajectory_msg(trajectory: Any) -> Any:
    """Convert a MoveItPy RobotTrajectory wrapper to a ROS message."""
    if hasattr(trajectory, 'get_robot_trajectory_msg'):
        return trajectory.get_robot_trajectory_msg()
    return trajectory

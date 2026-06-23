"""Explicit opt-in trajectory execution primitive for supervised hardware use."""

from typing import Any

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import PrimitiveResult


UR_ARM_JOINT_NAMES = (
    'shoulder_pan_joint',
    'shoulder_lift_joint',
    'elbow_joint',
    'wrist_1_joint',
    'wrist_2_joint',
    'wrist_3_joint',
)
MAX_SUPERVISED_SCALE = 0.25


def execute_planned_trajectory(
    planned_result: Any,
    execution_client: Any,
    safety: dict[str, Any] | None = None,
    expected_joint_names: list[str] | tuple[str, ...] | None = None,
    controller_name: str = 'scaled_joint_trajectory_controller',
    timeout_s: float = 30.0,
) -> PrimitiveResult:
    """Execute a planned joint trajectory only when explicitly enabled."""
    safety_settings = _safety_settings(safety)
    details = {
        'action_name': 'execute_planned_trajectory',
        'controller_name': controller_name,
        'safety': safety_settings,
    }
    if not safety_settings.get('allow_hardware_execution', False):
        return _blocked(
            'Hardware execution is disabled by safety config',
            FailureType.SAFETY_VIOLATION,
            details,
        )

    scale_failure = _scaling_failure(safety_settings)
    if scale_failure is not None:
        return _blocked(scale_failure, FailureType.SAFETY_VIOLATION, details)

    joint_trajectory = _joint_trajectory_from(planned_result)
    if joint_trajectory is None:
        return _blocked(
            'No joint trajectory available for execution',
            FailureType.SAFETY_VIOLATION,
            details,
        )

    joint_names = list(getattr(joint_trajectory, 'joint_names', []) or [])
    points = list(getattr(joint_trajectory, 'points', []) or [])
    details.update({
        'joint_names': joint_names,
        'point_count': len(points),
    })
    if not joint_names or not points:
        return _blocked(
            'Trajectory must contain joint names and points',
            FailureType.SAFETY_VIOLATION,
            details,
        )

    expected = list(expected_joint_names or UR_ARM_JOINT_NAMES)
    if joint_names != expected:
        details['expected_joint_names'] = expected
        return _blocked(
            'Trajectory joint names do not match the expected UR arm joints',
            FailureType.SAFETY_VIOLATION,
            details,
        )

    if execution_client is None:
        return _blocked(
            'No execution client was provided',
            FailureType.SAFETY_VIOLATION,
            details,
        )

    try:
        send_goal = getattr(execution_client, 'send_goal')
        client_result = send_goal(joint_trajectory, timeout_s=timeout_s)
    except Exception as exc:
        return _blocked(
            f'Trajectory execution request failed: {exc}',
            FailureType.UNKNOWN_FAILURE,
            details,
        )

    if isinstance(client_result, PrimitiveResult):
        return client_result

    success = bool(getattr(client_result, 'success', client_result))
    message = getattr(
        client_result,
        'message',
        'Trajectory execution accepted' if success else 'Trajectory execution failed',
    )
    result_details = dict(details)
    result_details['client_result'] = client_result
    if not success:
        return _blocked(message, FailureType.PATH_BLOCKED, result_details)

    return PrimitiveResult(
        success=True,
        message=message,
        details=result_details,
    )


def _safety_settings(safety: dict[str, Any] | None) -> dict[str, Any]:
    """Return the nested safety mapping used by config files and tests."""
    if safety is None:
        return {}
    return safety.get('safety', safety)


def _scaling_failure(safety: dict[str, Any]) -> str | None:
    """Return a failure message when motion scaling is not conservative."""
    velocity = float(safety.get('max_velocity_scale', 0.0))
    acceleration = float(safety.get('max_acceleration_scale', 0.0))
    if velocity <= 0.0 or acceleration <= 0.0:
        return 'Velocity and acceleration scaling must be positive'
    if velocity > MAX_SUPERVISED_SCALE:
        return 'Velocity scaling exceeds supervised hardware limit'
    if acceleration > MAX_SUPERVISED_SCALE:
        return 'Acceleration scaling exceeds supervised hardware limit'
    return None


def _joint_trajectory_from(planned_result: Any) -> Any | None:
    """Extract a JointTrajectory-like object from common result shapes."""
    if planned_result is None:
        return None

    trajectory = getattr(planned_result, 'trajectory', None)
    if trajectory is None and hasattr(planned_result, 'details'):
        trajectory = planned_result.details.get('trajectory')
    if trajectory is None and hasattr(planned_result, 'data'):
        trajectory = planned_result.data.get('trajectory')
    if trajectory is None:
        trajectory = planned_result

    if hasattr(trajectory, 'get_robot_trajectory_msg'):
        trajectory = trajectory.get_robot_trajectory_msg()

    return getattr(trajectory, 'joint_trajectory', trajectory)


def _blocked(
    message: str,
    failure_type: FailureType,
    details: dict[str, Any],
) -> PrimitiveResult:
    """Build a structured failed execution result."""
    failure = Failure(failure_type, message, dict(details))
    return PrimitiveResult(
        success=False,
        message=message,
        error_code=failure_type,
        failure=failure,
        details=dict(details),
    )

"""Robot motion helper primitive stubs beside the MoveItPy planner backend."""

from typing import Any

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import PrimitiveResult


def check_reachability(pose: Any) -> PrimitiveResult:
    """Check whether a pose is reachable using a deterministic stub."""
    # TODO: Replace this stub with MoveIt2 IK/planning-scene reachability.
    if not pose:
        failure = Failure(FailureType.POSE_UNKNOWN, 'Pose is unknown')
        return PrimitiveResult(
            success=False,
            message=failure.message,
            error_code=failure.failure_type,
            failure=failure,
            details={'action_name': 'check_reachability', 'pose': pose},
        )
    if isinstance(pose, dict) and pose.get('reachable') is False:
        failure = Failure(FailureType.NOT_REACHABLE, 'Pose is not reachable')
        return PrimitiveResult(
            success=False,
            message=failure.message,
            error_code=failure.failure_type,
            failure=failure,
            details={'action_name': 'check_reachability', 'pose': pose},
        )
    return PrimitiveResult(
        success=True,
        message='Pose is reachable',
        details={'action_name': 'check_reachability', 'pose': pose},
    )


def move_to_pose_stub(pose: Any) -> PrimitiveResult:
    """Move to a pose using a deterministic stub for non-MoveIt tests."""
    # TODO: Route this through the MoveIt2 planner backend when available.
    reachability = check_reachability(pose)
    if not reachability.success:
        return reachability
    return PrimitiveResult(
        success=True,
        message='Moved to pose',
        details={'action_name': 'move_to_pose_stub', 'pose': pose},
    )

"""
Perception primitive stubs.

Future perception integration should stay here behind structured primitive
results, leaving skills independent from ROS2 topics and services.
"""

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import PrimitiveResult


def detect_object(object_id: str) -> PrimitiveResult:
    """Detect an object using a deterministic plan-only stub."""
    # TODO: Replace this stub with perception topic/service integration.
    if not object_id:
        failure = Failure(
            FailureType.POSE_UNKNOWN,
            'Cannot detect an empty object id',
        )
        return PrimitiveResult(
            success=False,
            message=failure.message,
            error_code=failure.failure_type,
            failure=failure,
            details={'action_name': 'detect_object', 'object_id': object_id},
        )

    pose = {
        'frame_id': 'base_link',
        'position': {'x': 0.4, 'y': 0.0, 'z': 0.2},
        'orientation': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0},
    }
    return PrimitiveResult(
        success=True,
        message=f'Detected object: {object_id}',
        details={
            'action_name': 'detect_object',
            'object_id': object_id,
            'pose': pose,
            'confidence': 0.95,
        },
        world_updates={
            'objects': {
                object_id: {
                    'pose': pose,
                    'confidence': 0.95,
                    'reachable': True,
                },
            },
        },
    )

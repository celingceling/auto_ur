"""
Gripper primitive stubs.

Primitives are the boundary where future ROS2 gripper action/service calls
belong. Skills call these functions instead of talking to hardware directly.
"""

from auto_ur.core import PrimitiveResult


def open_gripper() -> PrimitiveResult:
    """Open the gripper using a deterministic plan-only stub."""
    # TODO: Replace this stub with a ROS2 gripper action or service call.
    return PrimitiveResult(
        success=True,
        message='Gripper opened',
        details={'action_name': 'open_gripper'},
    )


def close_gripper() -> PrimitiveResult:
    """Close the gripper using a deterministic plan-only stub."""
    # TODO: Replace this stub with a ROS2 gripper action or service call.
    return PrimitiveResult(
        success=True,
        message='Gripper closed',
        details={'action_name': 'close_gripper'},
    )

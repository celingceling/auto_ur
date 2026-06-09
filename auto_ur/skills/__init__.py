"""Plan-only composed demo skills."""

from auto_ur.skills.gripper_object_demo import gripper_object_demo
from auto_ur.skills.pick_place_demo import pick_and_place_demo

__all__ = [
    'gripper_object_demo',
    'pick_and_place_demo',
]

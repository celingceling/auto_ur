"""Plan-only composed demo skills."""

from auto_ur.skills.base import Skill
from auto_ur.skills.gripper_object_demo import gripper_object_demo
from auto_ur.skills.pick_object import PickObject
from auto_ur.skills.pick_place_demo import pick_and_place_demo
from auto_ur.skills.place_object import PlaceObject

__all__ = [
    'gripper_object_demo',
    'PickObject',
    'pick_and_place_demo',
    'PlaceObject',
    'Skill',
]

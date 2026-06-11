"""Failure taxonomy shared by primitives, skills, and future planners."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    """Small generic failure taxonomy for robot manipulation actions."""

    POSE_UNKNOWN = 'POSE_UNKNOWN'
    LOW_CONFIDENCE = 'LOW_CONFIDENCE'
    NOT_REACHABLE = 'NOT_REACHABLE'
    PATH_BLOCKED = 'PATH_BLOCKED'
    GRASP_FAILED = 'GRASP_FAILED'
    PLACE_FAILED = 'PLACE_FAILED'
    DESTINATION_OCCUPIED = 'DESTINATION_OCCUPIED'
    OBJECT_DROPPED = 'OBJECT_DROPPED'
    SAFETY_VIOLATION = 'SAFETY_VIOLATION'
    UNKNOWN_FAILURE = 'UNKNOWN_FAILURE'


@dataclass
class Failure:
    """Describe a structured action failure."""

    failure_type: FailureType
    message: str = ''
    details: dict[str, Any] = field(default_factory=dict)

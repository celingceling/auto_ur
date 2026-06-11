"""PickObject skill with symbolic checks and bounded local recovery."""

from __future__ import annotations

from typing import Any

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import RecoveryResult
from auto_ur.core import SkillResult
from auto_ur.primitives import close_gripper
from auto_ur.primitives import detect_object
from auto_ur.primitives import open_gripper
from auto_ur.skills.base import Skill


class PickObject(Skill):
    """Pick a known object and update symbolic holding state."""

    name = 'PickObject'

    def __init__(self, object_id: str, confidence_threshold: float = 0.5,
                 **kwargs: Any):
        """Create a pick skill for one object."""
        super().__init__(
            object_id=object_id,
            confidence_threshold=confidence_threshold,
            **kwargs,
        )
        self.object_id = object_id
        self.confidence_threshold = confidence_threshold

    def check_preconditions(self, world: Any) -> SkillResult:
        """Check pick preconditions against the symbolic world."""
        if not world.object_exists(self.object_id):
            return self._failure_result(
                FailureType.POSE_UNKNOWN,
                f'Unknown object: {self.object_id}',
                {'object_id': self.object_id},
            )
        if not world.pose_known(self.object_id):
            return self._failure_result(
                FailureType.POSE_UNKNOWN,
                f'Object pose unknown: {self.object_id}',
                {'object_id': self.object_id},
            )
        if not world.confidence_above(
            self.object_id,
            self.confidence_threshold,
        ):
            return self._failure_result(
                FailureType.LOW_CONFIDENCE,
                f'Object confidence below threshold: {self.object_id}',
                {'object_id': self.object_id},
            )
        if not world.object_reachable(self.object_id):
            return self._failure_result(
                FailureType.NOT_REACHABLE,
                f'Object is not reachable: {self.object_id}',
                {'object_id': self.object_id},
            )
        if not world.hand_empty():
            return self._failure_result(
                FailureType.GRASP_FAILED,
                'Robot hand is not empty',
                {'object_id': self.object_id},
            )
        if not world.gripper_ready():
            return self._failure_result(
                FailureType.GRASP_FAILED,
                'Gripper is not ready',
                {'object_id': self.object_id},
            )
        return SkillResult(
            success=True,
            message='Pick preconditions satisfied',
            details={'skill': self.name, 'object_id': self.object_id},
        )

    def execute(self, world: Any) -> SkillResult:
        """Run the pick sequence through primitive calls."""
        self.segment_summaries = []
        object_pose = world.objects[self.object_id].get('pose')
        for pose_name in ('pre_pick', 'pick'):
            result = self._plan_named_pose(pose_name, object_pose)
            if not result.success:
                return self._primitive_failure(
                    result,
                    FailureType.NOT_REACHABLE,
                    f'Pick motion failed at {pose_name}',
                )
            if pose_name == 'pre_pick':
                opened = open_gripper()
                if not opened.success:
                    return self._primitive_failure(
                        opened,
                        FailureType.GRASP_FAILED,
                        'Failed to open gripper',
                    )

        closed = close_gripper()
        if not closed.success:
            return self._primitive_failure(
                closed,
                FailureType.GRASP_FAILED,
                f'Failed to grasp object: {self.object_id}',
            )

        lift = self._plan_named_pose('lift', object_pose)
        if not lift.success:
            return self._primitive_failure(
                lift,
                FailureType.GRASP_FAILED,
                'Failed to lift grasped object',
            )

        return SkillResult(
            success=True,
            message=f'Picked object: {self.object_id}',
            details={
                'skill': self.name,
                'action_name': self.name,
                'object_id': self.object_id,
                'sequence': ['pre_pick', 'pick', 'lift'],
                'segment_summaries': self.segment_summaries,
                'end_state': self.start_state,
            },
            world_updates={
                'robot': {
                    'holding': self.object_id,
                    'hand_empty': False,
                },
                'objects': {
                    self.object_id: {
                        'state': 'held',
                        'location': 'gripper',
                    },
                },
            },
        )

    def check_postconditions(self, world: Any) -> SkillResult:
        """Verify that the object is held after picking."""
        if not world.holding(self.object_id) or world.hand_empty():
            return self._failure_result(
                FailureType.GRASP_FAILED,
                f'Robot is not holding object: {self.object_id}',
                {'object_id': self.object_id},
            )
        return SkillResult(
            success=True,
            message=f'Pick succeeded: {self.object_id}',
            details={'skill': self.name, 'object_id': self.object_id},
        )

    def local_recovery(self, world: Any,
                       failure: Failure | None) -> RecoveryResult:
        """Attempt bounded local pick recovery."""
        if failure is None:
            return RecoveryResult(False, 'No failure supplied')
        if failure.failure_type in (
            FailureType.POSE_UNKNOWN,
            FailureType.LOW_CONFIDENCE,
        ):
            detected = detect_object(self.object_id)
            return RecoveryResult(
                success=detected.success,
                message='Perception rescan completed',
                failure=detected.failure,
                details=detected.details,
                world_updates=detected.world_updates,
            )
        if failure.failure_type == FailureType.GRASP_FAILED:
            return RecoveryResult(
                success=True,
                message='Alternate grasp selected',
                details={
                    'skill': self.name,
                    'object_id': self.object_id,
                    'recovery': 'alternate_grasp_stub',
                },
            )
        if failure.failure_type == FailureType.NOT_REACHABLE:
            return RecoveryResult(
                success=False,
                message='Object reachability requires external planning',
                failure=failure,
            )
        return RecoveryResult(False, 'No local recovery available', failure)

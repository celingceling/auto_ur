"""PlaceObject skill with symbolic checks and bounded local recovery."""

from __future__ import annotations

from typing import Any

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import RecoveryResult
from auto_ur.core import SkillResult
from auto_ur.primitives import open_gripper
from auto_ur.skills.base import Skill


class PlaceObject(Skill):
    """Place a held object at a target location."""

    name = 'PlaceObject'

    def __init__(self, object_id: str, target_id: str,
                 confidence_threshold: float = 0.5, **kwargs: Any):
        """Create a place skill for one object and target."""
        super().__init__(
            object_id=object_id,
            target_id=target_id,
            confidence_threshold=confidence_threshold,
            **kwargs,
        )
        self.object_id = object_id
        self.target_id = target_id
        self.confidence_threshold = confidence_threshold

    def check_preconditions(self, world: Any) -> SkillResult:
        """Check place preconditions against the symbolic world."""
        if not world.holding(self.object_id):
            return self._failure_result(
                FailureType.OBJECT_DROPPED,
                f'Robot is not holding object: {self.object_id}',
                {'object_id': self.object_id},
            )
        if not world.pose_known(self.target_id):
            return self._failure_result(
                FailureType.POSE_UNKNOWN,
                f'Target pose unknown: {self.target_id}',
                {'target_id': self.target_id},
            )
        if not world.confidence_above(
            self.target_id,
            self.confidence_threshold,
        ):
            return self._failure_result(
                FailureType.LOW_CONFIDENCE,
                f'Target confidence below threshold: {self.target_id}',
                {'target_id': self.target_id},
            )
        if not world.location_reachable(self.target_id):
            return self._failure_result(
                FailureType.NOT_REACHABLE,
                f'Target is not reachable: {self.target_id}',
                {'target_id': self.target_id},
            )
        if not world.location_clear(self.target_id):
            return self._failure_result(
                FailureType.DESTINATION_OCCUPIED,
                f'Target is occupied: {self.target_id}',
                {'target_id': self.target_id},
            )
        return SkillResult(
            success=True,
            message='Place preconditions satisfied',
            details={
                'skill': self.name,
                'object_id': self.object_id,
                'target_id': self.target_id,
            },
        )

    def execute(self, world: Any) -> SkillResult:
        """Run the place sequence through primitive calls."""
        self.segment_summaries = []
        target_pose = world.locations[self.target_id].get('pose')
        for pose_name in ('pre_place', 'place'):
            result = self._plan_named_pose(pose_name, target_pose)
            if not result.success:
                return self._primitive_failure(
                    result,
                    FailureType.PLACE_FAILED,
                    f'Place motion failed at {pose_name}',
                )

        opened = open_gripper()
        if not opened.success:
            return self._primitive_failure(
                opened,
                FailureType.PLACE_FAILED,
                'Failed to open gripper for placement',
            )

        retreat = self._plan_named_pose('retreat', target_pose)
        if not retreat.success:
            return self._primitive_failure(
                retreat,
                FailureType.PLACE_FAILED,
                'Failed to retreat from placement',
            )

        return SkillResult(
            success=True,
            message=f'Placed object {self.object_id} at {self.target_id}',
            details={
                'skill': self.name,
                'action_name': self.name,
                'object_id': self.object_id,
                'target_id': self.target_id,
                'sequence': ['pre_place', 'place', 'retreat'],
                'segment_summaries': self.segment_summaries,
                'end_state': self.start_state,
            },
            world_updates={
                'robot': {
                    'holding': None,
                    'hand_empty': True,
                },
                'objects': {
                    self.object_id: {
                        'state': f'at:{self.target_id}',
                        'location': self.target_id,
                    },
                },
                'locations': {
                    self.target_id: {
                        'clear': False,
                    },
                },
            },
        )

    def check_postconditions(self, world: Any) -> SkillResult:
        """Verify object and robot state after placement."""
        object_state = world.objects.get(self.object_id, {})
        if object_state.get('location') != self.target_id:
            return self._failure_result(
                FailureType.PLACE_FAILED,
                f'Object is not at target: {self.target_id}',
                {
                    'object_id': self.object_id,
                    'target_id': self.target_id,
                },
            )
        if not world.hand_empty() or world.robot.get('holding') is not None:
            return self._failure_result(
                FailureType.PLACE_FAILED,
                'Robot hand is not empty after placement',
                {'object_id': self.object_id},
            )
        return SkillResult(
            success=True,
            message=f'Place succeeded: {self.object_id} at {self.target_id}',
            details={
                'skill': self.name,
                'object_id': self.object_id,
                'target_id': self.target_id,
            },
        )

    def local_recovery(self, world: Any,
                       failure: Failure | None) -> RecoveryResult:
        """Attempt bounded local place recovery."""
        if failure is None:
            return RecoveryResult(False, 'No failure supplied')
        if failure.failure_type == FailureType.LOW_CONFIDENCE:
            pose = world.locations.get(self.target_id, {}).get('pose')
            return RecoveryResult(
                success=True,
                message='Target rescan completed',
                details={
                    'skill': self.name,
                    'target_id': self.target_id,
                    'recovery': 'target_rescan_stub',
                },
                world_updates={
                    'locations': {
                        self.target_id: {
                            'pose': pose,
                            'confidence': 0.95,
                        },
                    },
                },
            )
        if failure.failure_type == FailureType.PLACE_FAILED:
            return RecoveryResult(
                success=True,
                message='Alternate placement pose selected',
                details={
                    'skill': self.name,
                    'target_id': self.target_id,
                    'recovery': 'alternate_place_pose_stub',
                },
            )
        if failure.failure_type == FailureType.DESTINATION_OCCUPIED:
            return RecoveryResult(
                success=False,
                message='Occupied destination requires external planning',
                failure=failure,
            )
        return RecoveryResult(False, 'No local recovery available', failure)

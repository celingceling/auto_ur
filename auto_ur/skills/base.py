"""
Base class for reusable robot skills.

Skills own preconditions, execution, postconditions, and bounded local
recovery. Global failure routing remains outside this library.
"""

from __future__ import annotations

from typing import Any

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import PrimitiveResult
from auto_ur.core import RecoveryResult
from auto_ur.core import SkillResult
from auto_ur.primitives import move_to_pose
from auto_ur.primitives import move_to_pose_stub
from auto_ur.primitives import planned_state_from_trajectory


class Skill:
    """Base contract for a reusable robot manipulation skill."""

    name = 'Skill'

    def __init__(self, **kwargs: Any):
        """Create a skill with optional motion-planning context."""
        self.arm = kwargs.pop('arm', None)
        self.named_poses = kwargs.pop('named_poses', {})
        self.tool_frame = kwargs.pop('tool_frame', 'tool0')
        self.robot_model = kwargs.pop('robot_model', None)
        self.planning_group = kwargs.pop('planning_group', 'ur_manipulator')
        self.start_state = kwargs.pop('start_state', None)
        self.parameters = kwargs
        self.segment_summaries: list[dict[str, Any]] = []

    def check_preconditions(self, world: Any) -> SkillResult:
        """Check whether the skill can run in the current world."""
        raise NotImplementedError

    def execute(self, world: Any) -> SkillResult:
        """Execute the skill body against the current world."""
        raise NotImplementedError

    def check_postconditions(self, world: Any) -> SkillResult:
        """Check whether the skill achieved its intended effects."""
        raise NotImplementedError

    def local_recovery(self, world: Any,
                       failure: Failure | None) -> RecoveryResult:
        """Attempt bounded local recovery for a known failure."""
        return RecoveryResult(
            success=False,
            message='No local recovery available',
            failure=failure,
        )

    def run(self, world: Any) -> SkillResult:
        """Run preconditions, execution, updates, and postconditions."""
        preconditions = self.check_preconditions(world)
        if not preconditions.success:
            recovered = self._recover(world, preconditions.failure)
            if not recovered.success:
                return preconditions
            preconditions = self.check_preconditions(world)
            if not preconditions.success:
                return preconditions

        executed = self.execute(world)
        if not executed.success:
            recovered = self._recover(world, executed.failure)
            if not recovered.success:
                return executed
            executed = self.execute(world)
            if not executed.success:
                return executed

        world.apply_updates(executed.world_updates)
        postconditions = self.check_postconditions(world)
        if not postconditions.success:
            return postconditions

        details = dict(executed.details)
        details.setdefault('skill', self.name)
        return SkillResult(
            success=True,
            message=postconditions.message or executed.message,
            details=details,
            world_updates=executed.world_updates,
        )

    def _recover(self, world: Any,
                 failure: Failure | None) -> RecoveryResult:
        """Run local recovery and apply its symbolic updates on success."""
        recovered = self.local_recovery(world, failure)
        if recovered.success:
            world.apply_updates(recovered.world_updates)
        return recovered

    def _plan_named_pose(self, pose_name: str,
                         fallback_pose: Any = None) -> PrimitiveResult:
        """Plan or stub a motion segment by pose name."""
        pose = self.named_poses.get(pose_name, fallback_pose)
        if self.arm is None:
            result = move_to_pose_stub(pose)
            self._append_segment(pose_name, result)
            return result

        result = move_to_pose(
            self.arm,
            pose,
            self.tool_frame,
            start_state=self.start_state,
        )
        end_state = planned_state_from_trajectory(
            self.robot_model,
            self.planning_group,
            result.details.get('trajectory'),
        )
        self._append_segment(pose_name, result, end_state=end_state)
        if result.success:
            self.start_state = end_state
        return result

    def _append_segment(self, pose_name: str, result: PrimitiveResult,
                        end_state: Any = None) -> None:
        """Record motion segment details for demo playback."""
        self.segment_summaries.append({
            'pose_name': pose_name,
            'success': result.success,
            'message': result.message,
            'trajectory': result.details.get('trajectory'),
            'start_state': self.start_state,
            'end_state': end_state,
        })

    def _failure_result(self, failure_type: FailureType, message: str,
                        details: dict[str, Any] | None = None) -> SkillResult:
        """Build a failed skill result."""
        failure = Failure(failure_type, message, details or {})
        return SkillResult(
            success=False,
            message=message,
            failure=failure,
            details={
                'skill': self.name,
                'parameters': self.parameters,
                **(details or {}),
            },
        )

    def _primitive_failure(self, result: PrimitiveResult,
                           fallback_type: FailureType,
                           message: str) -> SkillResult:
        """Convert a failed primitive result into a skill result."""
        failure = result.failure or Failure(
            fallback_type,
            message,
            result.details,
        )
        return SkillResult(
            success=False,
            message=message,
            failure=failure,
            details={
                'skill': self.name,
                'parameters': self.parameters,
                'segment_summaries': self.segment_summaries,
            },
        )

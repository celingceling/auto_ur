"""Compatibility wrapper for the class-based pick/place skills."""

from typing import Any

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import SkillResult
from auto_ur.skills.pick_object import PickObject
from auto_ur.skills.place_object import PlaceObject
from auto_ur.world_model import WorldModel


def pick_and_place_demo(arm: Any, config_loader: Any,
                        pick_pose_name: str,
                        place_pose_name: str,
                        tool_frame: str,
                        robot_model: Any = None,
                        planning_group: str = 'ur_manipulator',
                        start_state: Any = None) -> SkillResult:
    """Plan a pick/place sequence through structured skill classes."""
    poses_config = config_loader.load_named_cartesian_poses()
    named_poses = poses_config.get('named_cartesian_poses', {})
    pick_pose = named_poses.get(pick_pose_name)
    place_pose = named_poses.get(place_pose_name)
    if pick_pose is None or place_pose is None:
        missing = pick_pose_name if pick_pose is None else place_pose_name
        failure = Failure(
            FailureType.POSE_UNKNOWN,
            f'Unknown Cartesian pose: {missing}',
            {'pose_name': missing},
        )
        return SkillResult(
            success=False,
            message=failure.message,
            failure=failure,
            details={
                'action_name': 'pick_and_place_demo',
                'failed_segment': missing,
                'segment_summaries': [],
            },
        )

    world = WorldModel(
        objects={
            'specimen': {
                'pose': pick_pose,
                'confidence': 0.95,
                'reachable': True,
                'state': 'on_table',
            },
        },
        locations={
            'target': {
                'pose': place_pose,
                'confidence': 0.95,
                'reachable': True,
                'clear': True,
            },
        },
    )
    shared_context = {
        'arm': arm,
        'named_poses': named_poses,
        'tool_frame': tool_frame,
        'robot_model': robot_model,
        'planning_group': planning_group,
    }
    pick = PickObject(
        'specimen',
        start_state=start_state,
        **shared_context,
    )
    pick_result = pick.run(world)
    if not pick_result.success:
        return _demo_result(
            success=False,
            message=pick_result.message,
            failure=pick_result.failure,
            pick_result=pick_result,
        )

    place = PlaceObject(
        'specimen',
        'target',
        start_state=pick_result.details.get('end_state'),
        **shared_context,
    )
    place_result = place.run(world)
    return _demo_result(
        success=place_result.success,
        message=(
            'Pick/place plan-only sequence succeeded'
            if place_result.success else place_result.message
        ),
        failure=place_result.failure,
        pick_result=pick_result,
        place_result=place_result,
    )


def _demo_result(success: bool, message: str, failure: Failure | None,
                 pick_result: SkillResult,
                 place_result: SkillResult | None = None) -> SkillResult:
    """Combine skill results into the historical demo result shape."""
    segment_summaries = []
    sequence = []
    end_state = None
    for result in (pick_result, place_result):
        if result is None:
            continue
        sequence.extend(result.details.get('sequence', []))
        segment_summaries.extend(result.details.get('segment_summaries', []))
        end_state = result.details.get('end_state', end_state)

    return SkillResult(
        success=success,
        message=message,
        failure=failure,
        details={
            'action_name': 'pick_and_place_demo',
            'sequence': sequence,
            'segment_summaries': segment_summaries,
            'start_state': pick_result.details.get('start_state'),
            'end_state': end_state,
        },
    )

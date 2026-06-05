"""Arm-only pick/place planning demo composed from pose primitives."""

from typing import Any

from auto_ur.core import ActionResult
from auto_ur.primitives import move_to_pose


def pick_and_place_demo(arm: Any, config_loader: Any,
                        pick_pose_name: str,
                        place_pose_name: str,
                        tool_frame: str) -> ActionResult:
    """Plan an arm-only pick/place pose sequence."""
    poses_config = config_loader.load_named_cartesian_poses()
    named_poses = poses_config.get('named_cartesian_poses', {})
    sequence = _sequence_for(pick_pose_name, place_pose_name, named_poses)
    segment_summaries = []

    for pose_name in sequence:
        pose = named_poses.get(pose_name)
        if pose is None:
            return ActionResult(
                success=False,
                message=f'Unknown Cartesian pose: {pose_name}',
                data={
                    'action_name': 'pick_and_place_demo',
                    'failed_segment': pose_name,
                    'segment_summaries': segment_summaries,
                },
            )

        result = move_to_pose(arm, pose, tool_frame)
        segment_summaries.append({
            'pose_name': pose_name,
            'success': result.success,
            'message': result.message,
        })
        if not result.success:
            return ActionResult(
                success=False,
                message=f'Pick/place planning failed at {pose_name}',
                data={
                    'action_name': 'pick_and_place_demo',
                    'failed_segment': pose_name,
                    'segment_summaries': segment_summaries,
                },
            )

    return ActionResult(
        success=True,
        message='Pick/place plan-only sequence succeeded',
        data={
            'action_name': 'pick_and_place_demo',
            'pick_pose_name': pick_pose_name,
            'place_pose_name': place_pose_name,
            'sequence': sequence,
            'segment_summaries': segment_summaries,
        },
    )


def _sequence_for(pick_pose_name: str, place_pose_name: str,
                  named_poses: dict[str, Any]) -> list[str]:
    """Build the pick/place sequence for configured pose names."""
    candidate_sequence = [
        f'pre_{pick_pose_name}',
        pick_pose_name,
        'lift',
        f'pre_{place_pose_name}',
        place_pose_name,
        'retreat',
    ]
    if all(pose_name in named_poses for pose_name in candidate_sequence):
        return candidate_sequence
    return ['pre_pick', 'pick', 'lift', 'pre_place', 'place', 'retreat']

"""Visual gripper demo composed from plan-only pose primitives."""

from typing import Any

from auto_ur.core import ActionResult
from auto_ur.primitives import move_to_pose, planned_state_from_trajectory


def gripper_object_demo(arm: Any, config_loader: Any,
                        tool_frame: str,
                        robot_model: Any = None,
                        planning_group: str = 'ur_manipulator',
                        start_state: Any = None) -> ActionResult:
    """Plan a visual gripper pick-place sequence."""
    poses_config = config_loader.load_named_cartesian_poses()
    named_poses = poses_config.get('named_cartesian_poses', {})
    sequence = [
        'pre_pick',
        'pick',
        'lift',
        'pre_place',
        'place',
        'retreat',
    ]
    segment_summaries = []
    planned_start_state = start_state

    for pose_name in sequence:
        pose = named_poses.get(pose_name)
        if pose is None:
            return ActionResult(
                success=False,
                message=f'Unknown Cartesian pose: {pose_name}',
                data={
                    'action_name': 'gripper_object_demo',
                    'failed_segment': pose_name,
                    'segment_summaries': segment_summaries,
                },
            )

        result = move_to_pose(
            arm,
            pose,
            tool_frame,
            start_state=planned_start_state,
        )
        planned_end_state = planned_state_from_trajectory(
            robot_model,
            planning_group,
            result.data.get('trajectory'),
        )
        segment_summaries.append({
            'pose_name': pose_name,
            'success': result.success,
            'message': result.message,
            'trajectory': result.data.get('trajectory'),
            'start_state': planned_start_state,
            'end_state': planned_end_state,
        })
        if not result.success:
            return ActionResult(
                success=False,
                message=f'Gripper planning failed at {pose_name}',
                data={
                    'action_name': 'gripper_object_demo',
                    'failed_segment': pose_name,
                    'segment_summaries': segment_summaries,
                },
            )
        planned_start_state = planned_end_state

    return ActionResult(
        success=True,
        message='Gripper visual sequence planned successfully',
        data={
            'action_name': 'gripper_object_demo',
            'sequence': sequence,
            'segment_summaries': segment_summaries,
            'start_state': start_state,
            'end_state': planned_start_state,
        },
    )

"""Default action registry for the plan-only UR10e demo."""

from auto_ur import primitives as prims
from auto_ur.core import ActionSpec
from auto_ur.registry.action_registry import ActionRegistry
from auto_ur.skills import pick_and_place_demo


def build_default_registry() -> ActionRegistry:
    """Build the registry for the four demo actions."""
    reg = ActionRegistry()
    reg.register(
        ActionSpec(
            name='move_to_named_pose',
            tier='primitive',
            description='Plan to a named UR10e joint state.',
            required_inputs=['pose_name'],
            failure_modes=['unknown_pose', 'planning_failed'],
            safety_checks=['plan_only'],
            supports_dry_run=True,
            supports_plan_only=True,
        ),
        prims.move_to_named_pose,
    )
    reg.register(
        ActionSpec(
            name='move_to_joint_state',
            tier='primitive',
            description='Plan to explicit UR10e joint positions.',
            required_inputs=['joint_positions'],
            failure_modes=['invalid_joint_state', 'planning_failed'],
            safety_checks=['plan_only'],
            supports_dry_run=True,
            supports_plan_only=True,
        ),
        prims.move_to_joint_state,
    )
    reg.register(
        ActionSpec(
            name='move_to_pose',
            tier='primitive',
            description='Plan to a task-space end-effector pose.',
            required_inputs=['pose'],
            optional_inputs=['tool_frame'],
            failure_modes=['invalid_pose', 'ik_failed', 'planning_failed'],
            safety_checks=['plan_only'],
            supports_dry_run=True,
            supports_plan_only=True,
        ),
        prims.move_to_pose,
    )
    reg.register(
        ActionSpec(
            name='pick_and_place_demo',
            tier='skill',
            description='Plan an arm-only pick/place pose sequence.',
            required_inputs=['pick_pose_name', 'place_pose_name'],
            failure_modes=['unknown_pose', 'planning_failed'],
            safety_checks=['plan_only', 'no_gripper_control'],
            supports_dry_run=True,
            supports_plan_only=True,
        ),
        pick_and_place_demo,
    )
    return reg

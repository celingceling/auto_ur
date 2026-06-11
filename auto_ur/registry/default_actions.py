"""Default action registry for the plan-only UR10e demo."""

from auto_ur import primitives as prims
from auto_ur.core import ActionSpec
from auto_ur.registry.action_registry import ActionRegistry
from auto_ur.skills import pick_and_place_demo
from auto_ur.skills import PickObject
from auto_ur.skills import PlaceObject


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
    reg.register_skill(
        PickObject,
        ActionSpec(
            name='PickObject',
            tier='skill',
            description='Pick a known object with symbolic checks.',
            required_inputs=['object_id'],
            preconditions=[
                'object_exists',
                'pose_known',
                'confidence_above_threshold',
                'object_reachable',
                'hand_empty',
                'gripper_ready',
            ],
            postconditions=['holding_object', 'hand_not_empty'],
            failure_modes=[
                'POSE_UNKNOWN',
                'LOW_CONFIDENCE',
                'NOT_REACHABLE',
                'GRASP_FAILED',
            ],
            safety_checks=['plan_only'],
            supports_dry_run=True,
            supports_plan_only=True,
        ),
    )
    reg.register_skill(
        PlaceObject,
        ActionSpec(
            name='PlaceObject',
            tier='skill',
            description='Place a held object at a target location.',
            required_inputs=['object_id', 'target_id'],
            preconditions=[
                'holding_object',
                'target_pose_known',
                'target_reachable',
                'target_clear',
            ],
            postconditions=[
                'object_at_target',
                'hand_empty',
                'not_holding_object',
            ],
            failure_modes=[
                'POSE_UNKNOWN',
                'LOW_CONFIDENCE',
                'NOT_REACHABLE',
                'PLACE_FAILED',
                'DESTINATION_OCCUPIED',
            ],
            safety_checks=['plan_only'],
            supports_dry_run=True,
            supports_plan_only=True,
        ),
    )
    return reg

"""Tests for the structured auto_ur action-library contracts."""

from auto_ur.core import ActionResult
from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import PrimitiveResult
from auto_ur.core import RecoveryResult
from auto_ur.core import SkillResult
from auto_ur.primitives import check_reachability
from auto_ur.primitives import close_gripper
from auto_ur.primitives import detect_object
from auto_ur.primitives import move_to_pose_stub
from auto_ur.primitives import open_gripper
from auto_ur.registry.default_actions import build_default_registry
from auto_ur.skills import gripper_object_demo
from auto_ur.skills import pick_and_place_demo
from auto_ur.skills import PickObject
from auto_ur.skills import PlaceObject
from auto_ur.skills import Skill
from auto_ur.world_model import WorldModel
import pytest

# reusable fake cartesian pose
POSE = {
    'frame_id': 'base_link',
    'position': {'x': 0.4, 'y': 0.0, 'z': 0.2},
    'orientation': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0},
}

# list of expected failure taxonomy
EXPECTED_FAILURE_TYPES = {
    'POSE_UNKNOWN',
    'LOW_CONFIDENCE',
    'NOT_REACHABLE',
    'PATH_BLOCKED',
    'GRASP_FAILED',
    'PLACE_FAILED',
    'DESTINATION_OCCUPIED',
    'OBJECT_DROPPED',
    'SAFETY_VIOLATION',
    'UNKNOWN_FAILURE',
}

# fake MoveIt-style planning object so wrapper can test w/o running real MoveIt
class FakePlanResult:
    """MoveItPy-like successful plan result for wrapper tests."""

    trajectory = 'fake-trajectory'

    def __bool__(self):
        """Return true so primitives treat the fake plan as successful."""
        return True


class FakeArm:
    """Small fake planning component used by wrapper tests."""

    def __init__(self):
        """Create a fake arm with a call log."""
        self.calls = []

    def set_start_state_to_current_state(self):
        """Record current-state planning setup."""
        self.calls.append(('set_start_state_to_current_state', {}))

    def set_goal_state(self, **kwargs):
        """Record the requested goal state."""
        self.calls.append(('set_goal_state', kwargs))

    def plan(self):
        """Return a fake successful plan."""
        self.calls.append(('plan', {}))
        return FakePlanResult()

# fake config loader that returns 6 fixed demo poses
# use this instead of loading YAML bc only testing wrapper behavior
class FakeConfigLoader:
    """Small config loader exposing named Cartesian poses."""

    def load_named_cartesian_poses(self):
        """Return the fixed demo pose names used by compatibility wrappers."""
        names = [
            'pre_pick',
            'pick',
            'lift',
            'pre_place',
            'place',
            'retreat',
        ]
        return {'named_cartesian_poses': {name: POSE for name in names}}

# fake skill that fails once, recovers, then succeeds
class RecoveringExecutionSkill(Skill):
    """Fake skill that recovers once and then succeeds."""

    name = 'RecoveringExecutionSkill'

    def __init__(self):
        """Create a fake skill with call counters."""
        super().__init__()
        self.execute_calls = 0
        self.recovery_calls = 0

    def check_preconditions(self, world):
        """Pass preconditions."""
        return SkillResult(True, 'ready')

    def execute(self, world):
        """Fail once, then return a successful world update."""
        self.execute_calls += 1
        if self.execute_calls == 1:
            failure = Failure(
                FailureType.GRASP_FAILED,
                'first execution failed',
            )
            return SkillResult(False, 'failed once', failure=failure)
        return SkillResult(
            True,
            'executed',
            details={'execute_calls': self.execute_calls},
            world_updates={'robot': {'gripper_ready': False}},
        )

    def check_postconditions(self, world):
        """Pass only after the execution update is applied."""
        return SkillResult(
            success=world.robot.get('gripper_ready') is False,
            message='postconditions satisfied',
        )

    def local_recovery(self, world, failure):
        """Recover successfully one time."""
        self.recovery_calls += 1
        return RecoveryResult(
            True,
            'recovered',
            failure=failure,
            details={'recovery_calls': self.recovery_calls},
        )

# fake skill that keeps failing after recovery
class AlwaysFailAfterRecoverySkill(Skill):
    """Fake skill proving run() does not recover forever."""

    name = 'AlwaysFailAfterRecoverySkill'

    def __init__(self):
        """Create a fake skill with call counters."""
        super().__init__()
        self.execute_calls = 0
        self.recovery_calls = 0

    def check_preconditions(self, world):
        """Pass preconditions."""
        return SkillResult(True, 'ready')

    def execute(self, world):
        """Fail execution every time."""
        self.execute_calls += 1
        failure = Failure(FailureType.PLACE_FAILED, 'still failed')
        return SkillResult(False, 'still failed', failure=failure)

    def check_postconditions(self, world):
        """Postconditions are never reached."""
        return SkillResult(True, 'unused')

    def local_recovery(self, world, failure):
        """Report a successful recovery attempt."""
        self.recovery_calls += 1
        return RecoveryResult(True, 'recovered', failure=failure)

# normal world with object, target, and reachable/clear state
def make_world() -> WorldModel:
    """Create a nominal pick/place world."""
    return WorldModel(
        objects={
            'specimen': {
                'pose': POSE,
                'confidence': 0.95,
                'reachable': True,
                'state': 'on_table',
            },
        },
        locations={
            'target': {
                'pose': POSE,
                'confidence': 0.95,
                'reachable': True,
                'clear': True,
            },
        },
    )

# tests if result dataclasses are constructible and compatible
def test_structured_result_types_instantiate():
    """Verify primitive, skill, recovery, and failure contracts."""
    failure = Failure(FailureType.GRASP_FAILED, 'grasp failed') # create grasp failure object
    # make result objects
    primitive = PrimitiveResult(False, 'failed', failure=failure)
    skill = SkillResult(False, 'failed', failure=failure)
    recovery = RecoveryResult(True, 'recovered')

    assert primitive.failure is failure
    assert primitive.data is primitive.details
    assert skill.failure.failure_type == FailureType.GRASP_FAILED
    assert recovery.success is True

# tests backward compatibility for old ActionResult 
def test_action_result_accepts_data_and_details_aliases():
    """Verify ActionResult keeps old data usage compatible."""
    result = ActionResult(success=True, message='ok', data={'step': 'pick'})

    assert isinstance(result, PrimitiveResult)
    assert result.details == {'step': 'pick'}
    assert result.data is result.details

    result.data = {'step': 'place'}

    assert result.details == {'step': 'place'}

# test failure enums are as expected (this seems pointless but fine)
def test_failure_type_taxonomy_matches_architecture():
    """Verify the small generic failure taxonomy is present."""
    assert {failure.value for failure in FailureType} == EXPECTED_FAILURE_TYPES

# test helper methods and explicit update methods.
# pass means symbolic world can answer precondition questions and
# record pick/place effects
def test_world_model_helpers_and_updates():
    """Verify symbolic world helpers reflect state and updates."""
    world = make_world()

    assert world.object_exists('specimen')
    assert world.pose_known('specimen')
    assert world.confidence_above('specimen', 0.5)
    assert world.object_reachable('specimen')
    assert world.location_reachable('target')
    assert world.location_clear('target')
    assert world.hand_empty()

    world.update_robot_holding('specimen')
    world.update_object_location('specimen', 'target')

    assert world.holding('specimen')
    assert not world.hand_empty()
    assert world.objects['specimen']['location'] == 'target'

# tests worldmodel object and applies objects
# pass means primitive/skill world_updates can be applied to world model
def test_world_model_apply_updates_merges_symbolic_state():
    """Verify structured updates modify object, location, and robot state."""
    world = WorldModel()

    world.apply_updates({
        'objects': {
            'specimen': {
                'pose': POSE,
                'confidence': 0.8,
                'reachable': True,
            },
        },
        'locations': {
            'target': {
                'pose': POSE,
                'clear': True,
                'reachable': True,
            },
        },
        'robot': {
            'holding': 'specimen',
            'hand_empty': False,
        },
    })

    assert world.pose_known('specimen')
    assert world.confidence_above('specimen', 0.75)
    assert world.location_clear('target')
    assert world.holding('specimen')


# tests planner-style skill creation
# pass means planner can request skills by names and params (that they exist)
def test_registry_instantiates_structured_skills():
    """Verify planners can instantiate skills from action dictionaries."""
    registry = build_default_registry()

    pick = registry.instantiate({
        'skill': 'PickObject',
        'params': {'object_id': 'specimen'},
    })
    place = registry.instantiate({
        'skill': 'PlaceObject',
        'params': {'object_id': 'specimen', 'target_id': 'target'},
    })

    assert isinstance(pick, PickObject)
    assert isinstance(place, PlaceObject)

# test registry error handling
# pass means malformed planner requests fail clearly and cleanly
def test_registry_reports_malformed_action_dictionaries():
    """Verify registry failures are structured enough for planner callers."""
    registry = build_default_registry()

    with pytest.raises(ValueError, match='requires a skill or action key'):
        registry.instantiate({})

    with pytest.raises(KeyError, match='Unknown action'):
        registry.instantiate({'skill': 'MissingSkill', 'params': {}})

    with pytest.raises(ValueError, match='params must be a dictionary'):
        registry.instantiate({'skill': 'PickObject', 'params': []})

    with pytest.raises(ValueError, match='not instantiable skill'):
        registry.instantiate({'skill': 'move_to_pose', 'params': {}})

# test check_reachability w/ fake reachable pose, and injected false pose
# pass means function returns structued results
def test_reachability_primitive_returns_structured_result():
    """Verify primitive stubs return structured results."""
    reachable = check_reachability(POSE)
    blocked = check_reachability({'reachable': False})

    assert reachable.success is True
    assert isinstance(reachable, PrimitiveResult)
    assert blocked.success is False
    assert blocked.failure.failure_type == FailureType.NOT_REACHABLE

# test gripper and perception stubs
# pass means functions exist and run and follow result contract
def test_gripper_and_perception_primitives_return_structured_results():
    """Verify deterministic primitive stubs report structured outcomes."""
    opened = open_gripper()
    closed = close_gripper()
    detected = detect_object('specimen')
    missing = detect_object('')

    assert opened.success is True
    assert closed.success is True
    assert isinstance(opened, PrimitiveResult)
    assert detected.world_updates['objects']['specimen']['confidence'] == 0.95
    assert missing.success is False
    assert missing.failure.failure_type == FailureType.POSE_UNKNOWN

# test motion stub failure mapping
# pass means missing motion input detected and reported structurally
def test_move_to_pose_stub_reports_unknown_pose():
    """Verify the motion stub maps empty poses to POSE_UNKNOWN."""
    result = move_to_pose_stub(None)

    assert result.success is False
    assert result.failure.failure_type == FailureType.POSE_UNKNOWN

# test PickObject and PlaceObject
# pass means core structure pick/place flow works
def test_pick_then_place_updates_world_state():
    """Verify successful pick/place skills update symbolic state."""
    world = make_world()

    pick_result = PickObject('specimen').run(world)
    place_result = PlaceObject('specimen', 'target').run(world)

    assert pick_result.success is True
    assert place_result.success is True
    assert world.objects['specimen']['location'] == 'target'
    assert world.hand_empty()
    assert world.robot['holding'] is None

# tests pick local recovery from no object
# i don't see where local recovery is performed
def test_pick_recovers_unknown_object_with_perception_rescan():
    """Verify missing objects are currently recoverable by perception."""
    world = WorldModel()

    result = PickObject('specimen').run(world) # recovery is here

    assert result.success is True
    assert world.object_exists('specimen')
    assert world.holding('specimen')

# test pick recovery for known object with no pose
# pass means pose rescan recovery works
def test_pick_recovers_unknown_pose_with_perception_rescan():
    """Verify known objects without poses are currently recoverable."""
    world = WorldModel(objects={'specimen': {'pose': None}})

    result = PickObject('specimen').run(world)

    assert result.success is True
    assert world.pose_known('specimen')
    assert world.holding('specimen')

# tests pick recovery when given low confidence (meaning idk if i picked it up)
# pass means low-conf perception recovery works
def test_pick_recovers_low_confidence_with_rescan():
    """Verify low-confidence object pose uses local perception recovery."""
    world = make_world()
    world.objects['specimen']['confidence'] = 0.1

    result = PickObject('specimen').run(world)

    assert result.success is True
    assert world.objects['specimen']['confidence'] == 0.95 # assert new result is good

# test grasp failure types
# pass means pick does not ignore robot hand/gripper state
def test_pick_reports_hand_not_empty_and_gripper_not_ready():
    """Verify unrecoverable pick preconditions return GRASP_FAILED."""
    occupied_hand = make_world()
    occupied_hand.update_robot_holding('other_object')
    unready_gripper = make_world()
    unready_gripper.robot['gripper_ready'] = False

    occupied_result = PickObject('specimen').run(occupied_hand)
    unready_result = PickObject('specimen').run(unready_gripper)

    assert occupied_result.success is False
    assert occupied_result.failure.failure_type == FailureType.GRASP_FAILED
    assert unready_result.success is False
    assert unready_result.failure.failure_type == FailureType.GRASP_FAILED

# test unreachable object handling
# pass means unreachable pick reported for external planning (not solved internally)
def test_pick_reports_unreachable_for_external_planner():
    """Verify unreachable objects are not solved globally by the skill."""
    world = make_world()
    world.objects['specimen']['reachable'] = False

    result = PickObject('specimen').run(world)

    assert result.success is False
    assert result.failure.failure_type == FailureType.NOT_REACHABLE

# test two place precondition failures (object dropped, pose unknown)
# pass means place verifies holding object and knowing target pose
def test_place_reports_not_holding_and_unknown_target_pose():
    """Verify place failures for missing held object and target pose."""
    not_holding = make_world()
    unknown_target = make_world()
    unknown_target.update_robot_holding('specimen')
    unknown_target.locations['target']['pose'] = None

    not_holding_result = PlaceObject('specimen', 'target').run(not_holding)
    unknown_target_result = PlaceObject(
        'specimen',
        'target',
    ).run(unknown_target)

    assert not_holding_result.success is False
    assert not_holding_result.failure.failure_type == (
        FailureType.OBJECT_DROPPED
    )
    assert unknown_target_result.success is False
    assert unknown_target_result.failure.failure_type == (
        FailureType.POSE_UNKNOWN
    )

# test place recovery from low target conf
# pass means target rescan recovery works
def test_place_recovers_low_target_confidence():
    """Verify low target confidence uses bounded local recovery."""
    world = make_world()
    world.update_robot_holding('specimen')
    world.locations['target']['confidence'] = 0.1

    result = PlaceObject('specimen', 'target').run(world)

    assert result.success is True
    assert world.locations['target']['confidence'] == 0.95
    assert world.objects['specimen']['location'] == 'target'

# tests unreachable target handling
# pass means reports unreachable target
def test_place_reports_unreachable_target():
    """Verify unreachable targets are reported to external planners."""
    world = make_world()
    world.update_robot_holding('specimen')
    world.locations['target']['reachable'] = False

    result = PlaceObject('specimen', 'target').run(world)

    assert result.success is False
    assert result.failure.failure_type == FailureType.NOT_REACHABLE

# test occupied destination handling
# pass means place refuses occupied targets
def test_place_reports_occupied_destination():
    """Verify occupied targets are reported rather than globally solved."""
    world = make_world()
    world.update_robot_holding('specimen')
    world.locations['target']['clear'] = False

    result = PlaceObject('specimen', 'target').run(world)

    assert result.success is False
    assert result.failure.failure_type == FailureType.DESTINATION_OCCUPIED

# test retry behavior after local recovery
# pass means skill.run() does precond, execution, recovery retry, updates,
# and postcond in order
def test_skill_run_recovers_once_and_applies_execution_updates():
    """Verify Skill.run retries execution once after local recovery."""
    world = make_world()
    skill = RecoveringExecutionSkill()

    result = skill.run(world)

    assert result.success is True
    assert skill.execute_calls == 2
    assert skill.recovery_calls == 1
    assert world.robot['gripper_ready'] is False
    assert result.details['execute_calls'] == 2

# test bounded recovery
# pass means local recovery is bounded, not infinite loop
def test_skill_run_does_not_recover_forever():
    """Verify Skill.run returns the second execution failure directly."""
    world = make_world()
    skill = AlwaysFailAfterRecoverySkill()

    result = skill.run(world)

    assert result.success is False
    assert skill.execute_calls == 2
    assert skill.recovery_calls == 1
    assert result.failure.failure_type == FailureType.PLACE_FAILED

# Demo wrapper tests

# test arm-only compatibility wrapper
# pass menas old demo wrapper still exposes expected playback data w/ structured results
def test_pick_and_place_demo_wrapper_returns_combined_details():
    """Verify the compatibility wrapper reports the six-segment sequence."""
    result = pick_and_place_demo(
        FakeArm(),
        FakeConfigLoader(),
        'pick',
        'place',
        'tool0',
    )

    assert result.success is True
    assert result.details['sequence'] == [
        'pre_pick',
        'pick',
        'lift',
        'pre_place',
        'place',
        'retreat',
    ]
    assert len(result.details['segment_summaries']) == 6
    assert result.details['segment_summaries'][0]['trajectory'] == (
        'fake-trajectory'
    )

# tests current gripper demo behavior
# pass menas gripper demo still uses older hardcoded named-pose as expected
def test_gripper_object_demo_uses_fixed_named_pose_sequence():
    """Document that the gripper demo still uses the fixed pose path."""
    result = gripper_object_demo(FakeArm(), FakeConfigLoader(), 'tool0')

    assert result.success is True
    assert result.details['sequence'] == [
        'pre_pick',
        'pick',
        'lift',
        'pre_place',
        'place',
        'retreat',
    ]
    assert len(result.details['segment_summaries']) == 6

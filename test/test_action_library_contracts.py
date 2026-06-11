"""Tests for the structured auto_ur action-library contracts."""

from auto_ur.core import Failure
from auto_ur.core import FailureType
from auto_ur.core import PrimitiveResult
from auto_ur.core import RecoveryResult
from auto_ur.core import SkillResult
from auto_ur.primitives import check_reachability
from auto_ur.registry.default_actions import build_default_registry
from auto_ur.skills import PickObject
from auto_ur.skills import PlaceObject
from auto_ur.world_model import WorldModel


POSE = {
    'frame_id': 'base_link',
    'position': {'x': 0.4, 'y': 0.0, 'z': 0.2},
    'orientation': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0},
}


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


def test_structured_result_types_instantiate():
    """Verify primitive, skill, recovery, and failure contracts."""
    failure = Failure(FailureType.GRASP_FAILED, 'grasp failed')
    primitive = PrimitiveResult(False, 'failed', failure=failure)
    skill = SkillResult(False, 'failed', failure=failure)
    recovery = RecoveryResult(True, 'recovered')

    assert primitive.failure is failure
    assert primitive.data is primitive.details
    assert skill.failure.failure_type == FailureType.GRASP_FAILED
    assert recovery.success is True


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


def test_reachability_primitive_returns_structured_result():
    """Verify primitive stubs return structured results."""
    reachable = check_reachability(POSE)
    blocked = check_reachability({'reachable': False})

    assert reachable.success is True
    assert isinstance(reachable, PrimitiveResult)
    assert blocked.success is False
    assert blocked.failure.failure_type == FailureType.NOT_REACHABLE


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


def test_pick_recovers_low_confidence_with_rescan():
    """Verify low-confidence object pose uses local perception recovery."""
    world = make_world()
    world.objects['specimen']['confidence'] = 0.1

    result = PickObject('specimen').run(world)

    assert result.success is True
    assert world.objects['specimen']['confidence'] == 0.95


def test_pick_reports_unreachable_for_external_planner():
    """Verify unreachable objects are not solved globally by the skill."""
    world = make_world()
    world.objects['specimen']['reachable'] = False

    result = PickObject('specimen').run(world)

    assert result.success is False
    assert result.failure.failure_type == FailureType.NOT_REACHABLE


def test_place_reports_occupied_destination():
    """Verify occupied targets are reported rather than globally solved."""
    world = make_world()
    world.update_robot_holding('specimen')
    world.locations['target']['clear'] = False

    result = PlaceObject('specimen', 'target').run(world)

    assert result.success is False
    assert result.failure.failure_type == FailureType.DESTINATION_OCCUPIED

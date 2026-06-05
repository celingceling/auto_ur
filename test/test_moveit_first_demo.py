"""Tests for the MoveIt-first UR10e demo scaffold."""

import os
from pathlib import Path

from autoUR.config import ConfigLoader
from autoUR.core import ActionResult, ActionSpec
from autoUR.primitives import move_to_joint_state, move_to_pose
from autoUR.registry.default_actions import build_default_registry
from autoUR.skills import pick_and_place_demo
import pytest
import yaml


CONFIG_FILES = [
    'config/robots/ur10e.yaml',
    'config/poses/named_joint_states_ur10e.yaml',
    'config/poses/named_cartesian_poses.yaml',
    'config/demos/ur10e_plan_only_demo.yaml',
    'config/safety/default_motion_limits.yaml',
]


class FakePlanResult:
    """MoveItPy-like successful plan result for tests."""

    trajectory = 'fake-trajectory'

    def __bool__(self):
        """Return true so primitives treat the fake plan as successful."""
        return True


class FakeArm:
    """Small fake planning component used by primitive tests."""

    def __init__(self):
        """Create a fake arm with a call log."""
        self.calls = []

    def set_start_state_to_current_state(self):
        """Record start-state setup."""
        self.calls.append(('set_start_state_to_current_state', {}))

    def set_goal_state(self, **kwargs):
        """Record the requested goal state."""
        self.calls.append(('set_goal_state', kwargs))

    def plan(self):
        """Return a fake successful plan."""
        self.calls.append(('plan', {}))
        return FakePlanResult()


class FakeMoveIt:
    """Small fake MoveItPy object used by primitive tests."""

    planning_group = 'ur_manipulator'


def test_action_types_instantiate():
    """Verify the shared action data contracts instantiate."""
    spec = ActionSpec(
        name='move_to_pose',
        tier='primitive',
        description='Plan to a pose.',
        supports_plan_only=True,
    )
    result = ActionResult(success=True, message='ok')

    assert spec.name == 'move_to_pose'
    assert result.success is True


def test_config_files_parse_as_mappings():
    """Verify all demo YAML files parse as mappings."""
    package_root = Path(__file__).resolve().parents[1]

    for relative_path in CONFIG_FILES:
        config_path = package_root / relative_path
        with config_path.open('r', encoding='utf-8') as config_file:
            loaded_config = yaml.safe_load(config_file)

        assert isinstance(loaded_config, dict), relative_path


def test_config_loader_helpers_load_demo_configs():
    """Verify ConfigLoader loads each UR10e demo config family."""
    loader = ConfigLoader(config_root=Path(__file__).resolve().parents[1] / 'config')

    assert loader.load_robot('ur10e')['robot']['name'] == 'ur10e'
    assert 'ready' in loader.load_named_joint_states('ur10e')['named_joint_states']
    assert 'pick' in loader.load_named_cartesian_poses()['named_cartesian_poses']
    assert loader.load_demo('ur10e_plan_only_demo')['demo']['mode'] == 'plan_only'
    assert loader.load_safety()['safety']['allow_hardware_execution'] is False


def test_default_registry_contains_four_actions():
    """Verify the demo registry exposes exactly the planned actions."""
    reg = build_default_registry()

    assert reg.names() == [
        'move_to_named_pose',
        'move_to_joint_state',
        'move_to_pose',
        'pick_and_place_demo',
    ]
    assert len(reg.list()) == 4
    assert reg.get('move_to_pose').handler is move_to_pose


def test_primitives_plan_with_fake_arm():
    """Verify primitive functions plan with fake MoveIt-like objects."""
    fake_arm = FakeArm()
    joint_result = move_to_joint_state(
        FakeMoveIt(),
        fake_arm,
        None,
        {'shoulder_pan_joint': 0.0},
    )
    pose_result = move_to_pose(
        fake_arm,
        {
            'frame_id': 'base_link',
            'position': {'x': 0.4, 'y': 0.0, 'z': 0.3},
            'orientation': {'x': 0.0, 'y': 1.0, 'z': 0.0, 'w': 0.0},
        },
        'tool0',
    )

    assert joint_result.success is True
    assert pose_result.success is True
    assert not any(call[0] == 'execute' for call in fake_arm.calls)


def test_pick_and_place_demo_with_fake_arm():
    """Verify the composed demo skill plans each configured pose."""
    loader = ConfigLoader(config_root=Path(__file__).resolve().parents[1] / 'config')
    result = pick_and_place_demo(FakeArm(), loader, 'pick', 'place', 'tool0')

    assert result.success is True
    assert result.data['sequence'] == [
        'pre_pick',
        'pick',
        'lift',
        'pre_place',
        'place',
        'retreat',
    ]


def test_primitives_and_skills_do_not_execute():
    """Verify primitive and skill sources do not execute trajectories."""
    package_root = Path(__file__).resolve().parents[1]
    source_files = list((package_root / 'autoUR' / 'primitives').glob('*.py'))
    source_files += list((package_root / 'autoUR' / 'skills').glob('*.py'))

    for source_file in source_files:
        assert '.execute(' not in source_file.read_text(encoding='utf-8')


@pytest.mark.skipif(
    os.getenv('AUTOUR_RUN_MOVEIT_TESTS') != '1',
    reason='MoveIt integration smoke test is opt-in.',
)
def test_optional_moveit_named_joint_plan_smoke():
    """Optionally verify MoveItPy can be imported for integration testing."""
    from moveit.planning import MoveItPy

    assert MoveItPy is not None

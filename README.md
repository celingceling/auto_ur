# auto_ur

`auto_ur` is a ROS 2 Jazzy and MoveIt 2 plan-only demo package for UR-style
robot manipulation. It keeps the current MoveItPy planning backend, while
organizing reusable robot actions as a structured action library with typed
results, symbolic world state, skill preconditions/postconditions, bounded local
recovery hooks, and registry-based skill instantiation.

The package is intentionally plan-only. It can plan trajectories and replay
them in RViz for inspection, but it does not execute motion on hardware.

## Current Demos

- `demo_plan_only.launch.py`: arm-only UR10e plan-only demo.
- `gripper_object_demo.launch.py`: standalone UR10e + Robotiq visual replay
  demo. MoveItPy plans with an arm-only model while RViz visualizes the combined
  robot/gripper model.

Both demos publish planned trajectories for visualization/playback. Playback
nodes publish joint states for RViz only; they are not hardware controllers.

## Real Robot Preparation

The first real UR robot test should be arm-only and supervised. The existing
plan-only demos still do not move hardware. Hardware execution is available only
through the separate opt-in execution demo and only when
`allow_hardware_execution:=true` is passed.

### Info To Collect At The Robot

- UR model, such as `ur10e`, `ur5e`, or another supported UR type.
- Robot IP address.
- Computer network interface and IP address on the robot network.
- PolyScope version.
- Whether the External Control URCap is installed.
- Whether the External Control program exists on the teach pendant.
- Whether the robot calibration YAML has already been extracted.
- Mounted tool or gripper type, and whether it has a ROS 2 driver.
- Nearby obstacles, table location, object locations, and free workspace.
- Who will control the teach pendant and e-stop during testing.

### Install Or Verify The UR Driver

For ROS 2 Jazzy, use the official Universal Robots ROS 2 driver packages:

```bash
sudo apt update
sudo apt install ros-jazzy-ur
```

If the lab uses a custom UR driver branch, build that source workspace instead
and source it before launching `auto_ur`.

### Before Going To The Robot

Build and source the workspace:

```bash
cd ~/projects_ws/moveit_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select auto_ur
source install/setup.bash
```

Run the tests and plan-only demos:

```bash
python3 -m pytest -q test/test_action_library_contracts.py test/test_moveit_first_demo.py
ros2 launch auto_ur demo_plan_only.launch.py rviz:=true
ros2 launch auto_ur gripper_object_demo.launch.py rviz:=true
```

### At The Robot

Use this launch order before any future motion:

1. Verify the `auto_ur` plan-only demo still plans correctly.
2. Verify network connectivity to the robot IP.
3. Start the External Control program on the teach pendant.
4. Launch the official UR driver, or let the hardware demo include it.
5. Confirm `/joint_states` and the UR trajectory controller are active.
6. Review the planned trajectory details before enabling execution.

The hardware-readiness launch defaults to no execution:

```bash
ros2 launch auto_ur hardware_execution_demo.launch.py \
  ur_type:=ur10e \
  robot_name:=ur10e \
  robot_ip:=192.168.0.2 \
  launch_ur_driver:=false \
  allow_hardware_execution:=false
```

Only for a supervised arm-only test, after the UR driver and controller are
verified, opt in explicitly:

```bash
ros2 launch auto_ur hardware_execution_demo.launch.py \
  ur_type:=ur10e \
  robot_name:=ur10e \
  robot_ip:=192.168.0.2 \
  launch_ur_driver:=true \
  allow_hardware_execution:=true \
  pose_name:=ready
```

If your robot model is not `ur10e`, change `ur_type` and add a matching
`config/robots/<robot_name>.yaml` and
`config/poses/named_joint_states_<robot_name>.yaml` when model-specific limits
or named poses are needed.

## Library Shape

- `auto_ur/core/`: action metadata, structured result dataclasses, and failure
  taxonomy.
- `auto_ur/world_model.py`: dictionary-backed symbolic world model for objects,
  locations, and robot state.
- `auto_ur/primitives/`: low-level robot/perception operations. MoveItPy
  planning stays here; gripper, perception, and reachability are currently
  deterministic stubs.
- `auto_ur/skills/`: reusable skills such as `PickObject` and `PlaceObject`.
  Skills own preconditions, execution sequence, postconditions, and bounded
  local recovery.
- `auto_ur/registry/`: action catalog and skill-class instantiation from
  planner-style dictionaries.
- `auto_ur/nodes/`: ROS 2 demo nodes.

Global failure routing, LLM planning, TAMP, behavior-tree execution, and
hardware execution are outside this package for now.

## Build

From a ROS 2 Jazzy + MoveIt 2 environment:

```bash
cd ~/projects_ws/moveit_ws
colcon build --packages-select auto_ur
source install/setup.bash
```

If working directly from this Windows checkout in WSL, use a temporary colcon
workspace and symlink the package:

```bash
mkdir -p /tmp/auto_ur_ws/src
ln -sfn /mnt/c/Users/LICF/projects/auto_ur /tmp/auto_ur_ws/src/auto_ur
cd /tmp/auto_ur_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select auto_ur --symlink-install
source install/setup.bash
```

## Run The Arm-Only Demo

```bash
source /opt/ros/jazzy/setup.bash
source ~/projects_ws/moveit_ws/install/setup.bash
ros2 launch auto_ur demo_plan_only.launch.py
```

To keep RViz open for visual playback:

```bash
ros2 launch auto_ur demo_plan_only.launch.py rviz:=true
```

## Run The Gripper Visual Demo

```bash
source /opt/ros/jazzy/setup.bash
source ~/projects_ws/moveit_ws/install/setup.bash
ros2 launch auto_ur gripper_object_demo.launch.py
```

Use `rviz:=false` for a non-RViz launch smoke:

```bash
ros2 launch auto_ur gripper_object_demo.launch.py rviz:=false
```

## Use The Structured Skill Registry

Future planners can instantiate skills from action dictionaries:

```python
from auto_ur.registry.default_actions import build_default_registry
from auto_ur.world_model import WorldModel

registry = build_default_registry()
world = WorldModel(
    objects={
        "specimen": {
            "pose": {"frame_id": "base_link"},
            "confidence": 0.95,
            "reachable": True,
        },
    },
    locations={
        "target": {
            "pose": {"frame_id": "base_link"},
            "confidence": 0.95,
            "reachable": True,
            "clear": True,
        },
    },
)

pick = registry.instantiate({
    "skill": "PickObject",
    "params": {"object_id": "specimen"},
})
place = registry.instantiate({
    "skill": "PlaceObject",
    "params": {"object_id": "specimen", "target_id": "target"},
})

pick_result = pick.run(world)
place_result = place.run(world)
```

All primitives and skills return structured result objects such as
`PrimitiveResult`, `SkillResult`, and `RecoveryResult`. Do not return or depend
on bare booleans for action outcomes.

## Tests

Focused library and demo tests:

```bash
python3 -m pytest -q test/test_action_library_contracts.py
python3 -m pytest -q test/test_moveit_first_demo.py
```

Full package tests:

```bash
colcon test --packages-select auto_ur
colcon test-result --verbose
```

The optional MoveIt import smoke test is gated behind:

```bash
AUTO_UR_RUN_MOVEIT_TESTS=1 python3 -m pytest -q test/test_moveit_first_demo.py
```

## Safety Boundary

This repository plans and visualizes by default. Existing demo launch files do
not move hardware. Hardware execution is isolated behind
`execute_planned_trajectory(...)`, the supervised hardware safety config, and
the separate `hardware_execution_demo.launch.py` launch path.

Real gripper commands, perception services, reachability checks, collision
objects, and full hardware pick/place remain future work and should be reviewed
separately.

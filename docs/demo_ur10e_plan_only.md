# UR10e Plan-Only MoveItPy Demo

This demo verifies that auto_ur can request UR10e motion plans through MoveItPy.
It does not execute trajectories or move hardware.

## Prerequisites

- Ubuntu 24.04 with ROS 2 Jazzy.
- MoveIt 2 with MoveItPy available in the sourced environment.
- A compatible UR10e MoveIt planning context with the `ur_manipulator`
  planning group.

## Running

Build and source the workspace, then launch:

```bash
colcon build --packages-select auto_ur
source install/setup.bash
ros2 launch auto_ur demo_plan_only.launch.py
```

The demo node creates MoveItPy directly, loads UR10e YAML configuration, builds
the default registry, and runs the configured plan-only sequence.

The optional MoveIt integration smoke test is enabled with
`AUTO_UR_RUN_MOVEIT_TESTS=1`.

## Expected Behavior

The node logs each `ActionResult`. Successful results mean MoveIt produced a
plan for the requested target. The demo intentionally does not call
`execute()`, does not control a gripper, and does not attach collision objects.

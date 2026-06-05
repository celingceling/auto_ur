# UR10e Plan-Only MoveItPy Demo

This demo verifies that autoUR can request UR10e motion plans through MoveItPy.
It does not execute trajectories or move hardware.

## Prerequisites

- Ubuntu 24.04 with ROS 2 Jazzy.
- MoveIt 2 with MoveItPy available in the sourced environment.
- A compatible UR10e MoveIt planning context with the `ur_manipulator`
  planning group.

## Running

Build and source the workspace, then launch:

```bash
colcon build --packages-select autoUR
source install/setup.bash
ros2 launch autoUR demo_plan_only.launch.py
```

The demo node creates MoveItPy directly, loads UR10e YAML configuration, builds
the default registry, and runs the configured plan-only sequence.

## Expected Behavior

The node logs each `ActionResult`. Successful results mean MoveIt produced a
plan for the requested target. The demo intentionally does not call
`execute()`, does not control a gripper, and does not attach collision objects.

"""Launch the autoUR UR10e plan-only MoveItPy demo node."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Generate the plan-only demo launch description."""
    return LaunchDescription([
        Node(
            package='autoUR',
            executable='autoUR_demo_plan_only',
            output='screen',
        ),
    ])

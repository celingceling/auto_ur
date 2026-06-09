"""Launch the auto_ur UR10e plan-only MoveItPy demo node."""

import os

from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, Shutdown
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def _load_yaml(package_name, relative_path):
    """Load a YAML file from an installed package share directory."""
    import yaml

    package_path = get_package_share_directory(package_name)
    absolute_path = os.path.join(package_path, relative_path)
    with open(absolute_path, 'r', encoding='utf-8') as config_file:
        return yaml.safe_load(config_file)


def _load_text(package_name, relative_path):
    """Load a text file from an installed package share directory."""
    package_path = get_package_share_directory(package_name)
    absolute_path = os.path.join(package_path, relative_path)
    with open(absolute_path, 'r', encoding='utf-8') as text_file:
        return text_file.read()


def generate_launch_description():
    """Generate the plan-only demo launch description."""
    ur_type = LaunchConfiguration('ur_type')
    rviz = LaunchConfiguration('rviz')
    rviz_config_path = PathJoinSubstitution([
        FindPackageShare('auto_ur'),
        'config',
        'rviz',
        'demo_plan_only.rviz',
    ])
    robot_description_content = Command([
        'xacro ',
        PathJoinSubstitution([
            FindPackageShare('ur_description'),
            'urdf',
            'ur.urdf.xacro',
        ]),
        ' ur_type:=',
        ur_type,
        ' name:=',
        ur_type,
    ])
    robot_description = {
        'robot_description': ParameterValue(
            robot_description_content,
            value_type=str,
        ),
    }
    robot_description_semantic = {
        'robot_description_semantic': _load_text(
            'auto_ur',
            'config/moveit/ur10e.srdf',
        ),
    }
    kinematics_yaml = _load_yaml('auto_ur', 'config/moveit/kinematics.yaml')
    joint_limits_yaml = _load_yaml('auto_ur', 'config/moveit/joint_limits.yaml')
    ompl_yaml = _load_yaml('auto_ur', 'config/moveit/ompl_planning.yaml')
    controllers_yaml = _load_yaml(
        'auto_ur',
        'config/moveit/moveit_controllers.yaml',
    )
    moveit_py_yaml = _load_yaml('auto_ur', 'config/moveit/moveit_py.yaml')
    demo_node = Node(
        package='auto_ur',
        executable='auto_ur_demo_plan_only',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            joint_limits_yaml,
            ompl_yaml,
            controllers_yaml,
            moveit_py_yaml,
        ],
    )
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='log',
        arguments=['-d', rviz_config_path],
        parameters=[
            robot_description,
            robot_description_semantic,
        ],
        condition=IfCondition(rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'ur_type',
            default_value='ur10e',
            description='Universal Robots model type passed to ur_description.',
        ),
        DeclareLaunchArgument(
            'rviz',
            default_value='false',
            description='Launch RViz and keep helper nodes alive for recording.',
        ),
        Node(
            package='auto_ur',
            executable='auto_ur_trajectory_playback',
            name='auto_ur_trajectory_playback',
            output='log',
            parameters=[{
                'time_scale': 2.0,
                'hold_duration': 2.0,
            }],
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='log',
            parameters=[robot_description],
            remappings=[
                ('joint_states', '/auto_ur/joint_states'),
                ('/joint_states', '/auto_ur/joint_states'),
            ],
        ),
        rviz_node,
        demo_node,
        RegisterEventHandler(
            OnProcessExit(
                target_action=demo_node,
                on_exit=[Shutdown(reason='auto_ur demo completed')],
            ),
            condition=UnlessCondition(rviz),
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=rviz_node,
                on_exit=[Shutdown(reason='rviz closed')],
            ),
            condition=IfCondition(rviz),
        ),
    ])

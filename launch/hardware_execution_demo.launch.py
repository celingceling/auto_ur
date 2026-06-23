"""Launch a supervised opt-in UR arm hardware execution demo."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
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
    """Generate the hardware execution demo launch description."""
    ur_type = LaunchConfiguration('ur_type')
    robot_name = LaunchConfiguration('robot_name')
    robot_ip = LaunchConfiguration('robot_ip')
    launch_ur_driver = LaunchConfiguration('launch_ur_driver')
    allow_hardware_execution = LaunchConfiguration('allow_hardware_execution')
    pose_name = LaunchConfiguration('pose_name')
    controller_name = LaunchConfiguration('controller_name')
    action_topic = LaunchConfiguration('action_topic')
    safety_config = LaunchConfiguration('safety_config')

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
        'config/moveit/hardware_moveit_controllers.yaml',
    )
    moveit_py_yaml = _load_yaml('auto_ur', 'config/moveit/moveit_py.yaml')

    ur_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ur_robot_driver'),
                'launch',
                'ur_control.launch.py',
            ]),
        ]),
        launch_arguments={
            'ur_type': ur_type,
            'robot_ip': robot_ip,
            'launch_rviz': 'false',
        }.items(),
        condition=IfCondition(launch_ur_driver),
    )

    demo_node = Node(
        package='auto_ur',
        executable='auto_ur_hardware_execution_demo',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            joint_limits_yaml,
            ompl_yaml,
            controllers_yaml,
            moveit_py_yaml,
            {
                'robot_name': robot_name,
                'pose_name': pose_name,
                'safety_config': safety_config,
                'allow_hardware_execution': ParameterValue(
                    allow_hardware_execution,
                    value_type=bool,
                ),
                'controller_name': controller_name,
                'action_topic': action_topic,
            },
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'ur_type',
            default_value='ur10e',
            description='Universal Robots model passed to ur_description.',
        ),
        DeclareLaunchArgument(
            'robot_name',
            default_value='ur10e',
            description='auto_ur config robot name for YAML lookup.',
        ),
        DeclareLaunchArgument(
            'robot_ip',
            default_value='192.168.0.2',
            description='Robot IP used only when launch_ur_driver is true.',
        ),
        DeclareLaunchArgument(
            'launch_ur_driver',
            default_value='false',
            description='Also launch ur_robot_driver ur_control.launch.py.',
        ),
        DeclareLaunchArgument(
            'allow_hardware_execution',
            default_value='false',
            description='Must be true before any trajectory is sent.',
        ),
        DeclareLaunchArgument(
            'pose_name',
            default_value='ready',
            description='Named joint pose to plan and execute.',
        ),
        DeclareLaunchArgument(
            'controller_name',
            default_value='scaled_joint_trajectory_controller',
            description='UR trajectory controller name.',
        ),
        DeclareLaunchArgument(
            'action_topic',
            default_value=(
                '/scaled_joint_trajectory_controller/'
                'follow_joint_trajectory'
            ),
            description='FollowJointTrajectory action topic.',
        ),
        DeclareLaunchArgument(
            'safety_config',
            default_value='supervised_hardware_motion_limits',
            description='Safety config file name without .yaml.',
        ),
        ur_driver,
        demo_node,
    ])

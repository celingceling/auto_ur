from glob import glob

from setuptools import find_packages, setup

package_name = 'auto_ur'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/docs', glob('docs/*.md')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config/demos',
            glob('config/demos/*.yaml')),
        ('share/' + package_name + '/config/moveit',
            glob('config/moveit/*')),
        ('share/' + package_name + '/config/poses',
            glob('config/poses/*.yaml')),
        ('share/' + package_name + '/config/robots',
            glob('config/robots/*.yaml')),
        ('share/' + package_name + '/config/rviz',
            glob('config/rviz/*.rviz')),
        ('share/' + package_name + '/config/safety',
            glob('config/safety/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='celing-24-04',
    maintainer_email='celing-24-04@todo.todo',
    description='MoveItPy-first UR10e plan-only demo package',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'auto_ur = auto_ur.auto_ur:main',
            'auto_ur_demo_plan_only = auto_ur.nodes.demo_plan_only:main',
            'auto_ur_fake_joint_state_publisher = '
            'auto_ur.nodes.fake_joint_state_publisher:main',
            'auto_ur_trajectory_playback = '
            'auto_ur.nodes.trajectory_playback:main',
            'auto_ur_floor_marker_publisher = '
            'auto_ur.nodes.floor_marker_publisher:main',
        ],
    },
)

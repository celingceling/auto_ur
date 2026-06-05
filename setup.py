from glob import glob

from setuptools import find_packages, setup

package_name = 'autoUR'

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
        ('share/' + package_name + '/config/poses',
            glob('config/poses/*.yaml')),
        ('share/' + package_name + '/config/robots',
            glob('config/robots/*.yaml')),
        ('share/' + package_name + '/config/safety',
            glob('config/safety/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='celing-24-04',
    maintainer_email='celing-24-04@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'autoUR = autoUR.autoUR:main',
            'autoUR_demo_plan_only = autoUR.nodes.demo_plan_only:main',
        ],
    },
)

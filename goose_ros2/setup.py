from setuptools import setup

package_name = 'goose_ros2'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'camera_node = goose_ros2.camera_node:main',
            'lane_node = goose_ros2.lane_node:main',
            'control_node = goose_ros2.control_node:main',
            'motor_node = goose_ros2.motor_node:main',
        ],
    },
)
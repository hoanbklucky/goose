from glob import glob
from setuptools import setup

package_name = 'goosebot_hw'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/urdf', glob('urdf/*.xacro')),
        ('share/' + package_name + '/calibration', glob('calibration/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='goose',
    maintainer_email='you@example.com',
    description='Goosebot hardware bringup',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'motor_driver_node = goosebot_hw.motor_driver_node:main',
            'imu_node = goosebot_hw.imu_node:main',
            'tof_node = goosebot_hw.tof_node:main',
            'stereo_camera_node = goosebot_hw.stereo_camera_node:main',
            'cmd_vel_mux_node = goosebot_hw.cmd_vel_mux_node:main',
            'cmd_vel_to_odom = goosebot_hw.cmd_vel_to_odom:main',
        ],
    },
)

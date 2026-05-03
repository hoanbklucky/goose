from setuptools import setup

package_name = 'goose_ros2'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        (
            'share/' + package_name,
            ['package.xml'],
        ),

	(
            'share/' + package_name + '/launch',
       	    ['launch/bringup.launch.py'],
   	 ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hoanngo',
    maintainer_email='ngothanhhoan@gmail.com',
    description='Goose ROS2 package',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'perception_node = goose_ros2.perception_node:main',
            'control_node = goose_ros2.control_node:main',
            'motor_node = goose_ros2.motor_node:main',
            'web_stream_node = goose_ros2.web_stream_node:main',
            'keyboard_node = goose_ros2.keyboard_node:main',
        ],
    },
)

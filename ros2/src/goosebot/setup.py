from setuptools import setup
import os
from glob import glob


package_name = 'goosebot'


setup(
    name=package_name,

    version='0.0.1',

    packages=[package_name],

    data_files=[

        # Register package information
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),

        # Install package.xml
        (
            'share/' + package_name,
            ['package.xml']
        ),

        # Install launch files
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')
        ),

        # Install configuration files
        (
            os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')
        ),

    ],


    install_requires=[
        'setuptools'
    ],


    zip_safe=True,


    maintainer='Goosebot Developer',

    maintainer_email='user@example.com',


    description=
    'ROS2 package for the Goosebot autonomous RC car.',


    license='Apache-2.0',


    tests_require=[
        'pytest'
    ],


    entry_points={

        'console_scripts': [

            # Future ROS2 nodes
            #
            # Example:
            #
            # 'encoder_node = goosebot.encoder_node:main',
            #
            # 'motor_node = goosebot.motor_node:main',

        ],

    },

)

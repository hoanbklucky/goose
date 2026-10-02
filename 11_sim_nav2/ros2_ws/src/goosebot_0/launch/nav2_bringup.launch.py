import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
from launch.conditions import UnlessCondition
from launch.substitutions import PythonExpression
from nav2_common.launch import RewrittenYaml
from launch_ros.actions import Node


def generate_launch_description():
    goosebot_share = get_package_share_directory('goosebot_0')
    nav2_bringup_share = get_package_share_directory('nav2_bringup')

    default_params_file = os.path.join(goosebot_share, 'config', 'nav2_params.yaml')
    default_map_file = os.path.join(goosebot_share, 'maps', 'map.yaml')

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to the Nav2 params file'
    )
    map_file_arg = DeclareLaunchArgument(
        'map',
        default_value=default_map_file,
        description='Full path to the baked ground-truth map yaml'
    )
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='true in Gazebo sim (needs the /clock bridge); '
                     'false on hardware, which has no /clock'
    )
    slam_arg = DeclareLaunchArgument(
        'slam', default_value='false',
        description="true: use RTAB-Map's live /rtabmap/map (run stereo_slam.launch.py) "
                    "instead of the baked ground-truth map + ground-truth "
                    "map->odom bridge. The two MUST NOT run together: both "
                    "publish map->odom.")
    slam = LaunchConfiguration('slam')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # With slam:=true the static layers read RTAB-Map's /rtabmap/map (rtabmap_launch
    # runs in the /rtabmap namespace) instead of the map_server's /projected_map. Only the two static layers define a
    # 'map_topic' key, so a key-level rewrite is enough.
    nav2_params = RewrittenYaml(
        source_file=LaunchConfiguration('params_file'),
        root_key='',
        param_rewrites={
            'map_topic': PythonExpression(
                ["'/rtabmap/map' if '", slam, "' == 'true' else '/projected_map'"]),
        },
        convert_types=True,
    )

    # navigation_launch.py only -- NOT bringup_launch.py, since bringup_launch.py
    # also starts its own AMCL, which we don't want: localization here comes
    # from Gazebo ground truth via ground_truth_map_odom_bridge below, and the
    # map is a pre-baked ground-truth map, not something built live by SLAM.
    #
    # NOTE: this whole file's localization strategy (ground_truth_bridge,
    # below) only exists in sim. Setting use_sim_time:=false here does NOT
    # make this file hardware-ready -- see the ground_truth_bridge comment
    # below and the chat writeup for what a hardware bringup actually needs.
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_share, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': nav2_params,
        }.items()
    )

    # Serves the baked ground-truth map. Remapped so it publishes on
    # /projected_map -- matches what nav2_params.yaml's static_layer already
    # expects, no params file changes needed for this swap.
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'yaml_filename': LaunchConfiguration('map'),
            'use_sim_time': use_sim_time,
        }],
        remappings=[('/map', '/projected_map')],
        condition=UnlessCondition(slam),
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': ['map_server'],
        }],
        condition=UnlessCondition(slam),
    )

    # SIM-ONLY: subscribes to /ground_truth/pose, which comes from gz-sim's
    # OdometryPublisher plugin (robot.urdf.xacro) and does not exist on
    # hardware. Do not include this node in a hardware bringup launch file --
    # there is currently no replacement wired up (see chat writeup: needs
    # AMCL, navsat_transform_node+global EKF, or another real localization
    # source before Nav2 will have a map->odom transform on hardware at all).
    ground_truth_bridge = Node(
        package='goosebot_0',
        executable='ground_truth_map_odom_bridge.py',
        name='ground_truth_map_odom_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        condition=UnlessCondition(slam),
    )

    return LaunchDescription([
        params_file_arg,
        map_file_arg,
        use_sim_time_arg,
        slam_arg,
        map_server,
        lifecycle_manager,
        ground_truth_bridge,
        nav2_navigation,
    ])

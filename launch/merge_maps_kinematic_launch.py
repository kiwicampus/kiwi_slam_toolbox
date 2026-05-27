from launch import LaunchDescription
import launch_ros.actions
from launch_ros.actions import Node
from launch.actions import GroupAction
import os
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
def generate_launch_description():
    default_segmapping_file = os.getenv("SEGMAP_FILE", "/workspace/maps2d/segmapping/USI.yaml")
    segmapping_file = LaunchConfiguration("segmapping_file", default=default_segmapping_file)
    print(f"SEGMAPPING FILE: {default_segmapping_file}")

    declare_segmapping_file_cmd = DeclareLaunchArgument(
        "segmapping_file",
        default_value=default_segmapping_file,
        description="Full path to the ROS2 parameters file to use for all launched nodes",
    )
    
    start_map_server_node = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        namespace="",
        parameters=[
            {"yaml_filename": segmapping_file},
            {"use_sim_time": True},
        ],
        remappings=[
            ("map", "segmap"),
            ("map_metadata", "segmap_metadata"),
        ],
    )
    start_lifecycle_manager_node = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        namespace="",
        name="lifecycle_manager_localization",
        output="screen",
        arguments=["--ros-args", "--log-level", "info"],
        sigterm_timeout="20",
        sigkill_timeout="20",
        parameters=[
            {"autostart": True},
            {
                "node_names": [
                    "map_server",
                ]
            },
        ],
    )
    map_server_nodes = GroupAction(
        actions=[
            start_map_server_node,
            start_lifecycle_manager_node,
        ]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        parameters=[{"use_sim_time": True}],
        arguments=[
            "-d",
            "/workspace/rover/ros2/src/location/kiwi_slam_toolbox/config/slam_toolbox_merging.rviz",
        ],
    )

    return LaunchDescription(
        [
            declare_segmapping_file_cmd,
            launch_ros.actions.Node(
                package="slam_toolbox",
                executable="merge_maps_kinematic",
                name="slam_toolbox",
                output="screen",
            ),
            map_server_nodes,
            rviz_node,
        ]
    )

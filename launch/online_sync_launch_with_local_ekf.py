import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    LogInfo,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.actions import GroupAction
from launch.substitutions import AndSubstitution, LaunchConfiguration, NotSubstitution
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition


def generate_launch_description():
    autostart = LaunchConfiguration("autostart")
    use_lifecycle_manager = LaunchConfiguration("use_lifecycle_manager")
    use_sim_time = LaunchConfiguration("use_sim_time")
    slam_params_file = LaunchConfiguration("slam_params_file")

    slam_toolbox_dir = get_package_share_directory("slam_toolbox")
    parameters_file_dir = os.path.join(
        slam_toolbox_dir, "config", "mapping_localization_params.yaml"
    )
    default_segmapping_file = os.getenv("SEGMAP_FILE", "/workspace/maps2d/segmapping/USI.yaml")
    segmapping_file = LaunchConfiguration("segmapping_file", default=default_segmapping_file)
    print(f"SEGMAPPING FILE: {default_segmapping_file}")
    
    localization_params = LaunchConfiguration(
        "localization_params", default=parameters_file_dir
    )
    rl_debug_lvl = os.getenv("RL_DEBUG_LEVEL", "WARN")

    declare_localization_params_cmd = DeclareLaunchArgument(
        "localization_params",
        default_value=parameters_file_dir,
        description="Full path to the ROS2 parameters file to use for all launched nodes",
    )
    declare_autostart_cmd = DeclareLaunchArgument(
        "autostart",
        default_value="true",
        description="Automatically startup the slamtoolbox. "
        "Ignored when use_lifecycle_manager is true.",
    )
    declare_use_lifecycle_manager = DeclareLaunchArgument(
        "use_lifecycle_manager",
        default_value="false",
        description="Enable bond connection during node activation",
    )
    declare_use_sim_time_argument = DeclareLaunchArgument(
        "use_sim_time", default_value="true", description="Use simulation/Gazebo clock"
    )
    declare_slam_params_file_cmd = DeclareLaunchArgument(
        "slam_params_file",
        default_value=os.path.join(
            get_package_share_directory("slam_toolbox"),
            "config",
            "mapper_params_online_sync.yaml",
        ),
        description="Full path to the ROS2 parameters file to use for the slam_toolbox node",
    )

    start_sync_slam_toolbox_node = LifecycleNode(
        parameters=[
            slam_params_file,
            {
                "use_lifecycle_manager": use_lifecycle_manager,
                "use_sim_time": use_sim_time,
            },
        ],
        package="slam_toolbox",
        executable="sync_slam_toolbox_node",
        name="slam_toolbox",
        output="screen",
        namespace="",
    )

    configure_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(start_sync_slam_toolbox_node),
            transition_id=Transition.TRANSITION_CONFIGURE,
        ),
        condition=IfCondition(
            AndSubstitution(autostart, NotSubstitution(use_lifecycle_manager))
        ),
    )

    activate_event = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=start_sync_slam_toolbox_node,
            start_state="configuring",
            goal_state="inactive",
            entities=[
                LogInfo(msg="[LifecycleLaunch] Slamtoolbox node is activating."),
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_action(
                            start_sync_slam_toolbox_node
                        ),
                        transition_id=Transition.TRANSITION_ACTIVATE,
                    )
                ),
            ],
        ),
        condition=IfCondition(
            AndSubstitution(autostart, NotSubstitution(use_lifecycle_manager))
        ),
    )

    start_local_ekf_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node_odom",
        output="screen",
        parameters=[
            localization_params,
            {"use_sim_time": use_sim_time},
            {"imu0_differential": True},
        ],
        remappings=[
            ("odometry/filtered", "odometry/local2"),
            ("set_pose", "/ekf_local/set_pose"),
        ],
        arguments=["--ros-args", "--log-level", rl_debug_lvl],
        respawn=False,
    )
    start_local_ekf_node_map = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node_map",
        output="screen",
        parameters=[
            localization_params,
            {"use_sim_time": use_sim_time},
            {"imu0_differential": True},
        ],
        remappings=[
            ("odometry/filtered", "odometry/global2"),
            ("set_pose", "/ekf_local/set_pose"),
        ],
        arguments=["--ros-args", "--log-level", rl_debug_lvl],
        respawn=False,
    )
    start_average_imu_node = Node(
        package="location",
        executable="average_imu",
        name="average_imu",
        output="screen",
        parameters=[localization_params, {"use_sim_time": use_sim_time}],
        respawn=False,
    )
    start_map_server_node = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        namespace="",
        parameters=[
            {"yaml_filename": segmapping_file},
            {"use_sim_time": use_sim_time},
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

    imu_tf_publisher = Node(
                package="imu",
                executable="imu_tf_publisher",
                name="imu_tf_publisher",
            )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
        arguments=[
            "-d",
            "/workspace/rover/ros2/src/location/kiwi_slam_toolbox/config/slam_toolbox_default.rviz",
        ],
    )
    ld = LaunchDescription()

    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_use_lifecycle_manager)
    ld.add_action(declare_use_sim_time_argument)
    ld.add_action(declare_slam_params_file_cmd)
    ld.add_action(declare_localization_params_cmd)
    ld.add_action(start_sync_slam_toolbox_node)
    ld.add_action(configure_event)
    ld.add_action(activate_event)
    ld.add_action(start_local_ekf_node)
    ld.add_action(start_local_ekf_node_map)
    ld.add_action(start_average_imu_node)
    ld.add_action(map_server_nodes)
    ld.add_action(rviz_node)
    ld.add_action(imu_tf_publisher)
    return ld

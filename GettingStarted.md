
# Mapping guide
## Pre-mapping
### 1. Download rosbags
Your files could look like this for example:
```
📦workspace
 ┗ 📂rosbags
   ┗ 📂mapping2d
     ┣ 📂mor
     ┃ ┣📜mor_campus2_0.mcap
     ┃ ┣📜mor_campus2_0.mcap
     ┃ ┗📜mor_storage1_0.mcap
     ┗ 📂usi
       ┣📜usi_campus1_0.mcap
       ┗📜usi_campus2_0.mcap
```
### 2. Run script to extract initial pose from the rosbag 
Set the following variables depending of the folder where you downloaded the rosbags and choose the first one. For instance:
```bash
export ROSBAG_NAME=mor_storage_0
export ROSBAG_FOLDER=/workspace/rosbags/mapping2d/mor
export ROSBAG_PATH=$ROSBAG_FOLDER/$ROSBAG_NAME.mcap 
```
Run script
```bash
python3 /workspace/scripts/get_initial_pose_from_rosbag.py --input $ROSBAG_PATH 
```

You will get something that looks like this:
```bash
Add the following to the localization_params.yaml file:
    initial_state: [450.3216783544306, 959.1554233038154, 0.0, 0.0, 0.0, 2.1179507189976228, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    initial_estimate_covariance: [0.0015210288896311376, 0.0015210292179516087, 9.993727174498896e-07, 9.98746613299191e-07, 9.98746613299191e-07, 0.0008120560250521425, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

After mapping, if you want to edit the map (optional), add the following to the mapper_params_online_sync.yaml file:
map_start_pose: [450.3216783544306, 959.1554233038154, 2.1179507189976228]
```

### 4. Update localization_params.yaml file 
Open the file in `/workspace/rover/ros2/src/location/kiwi_slam_toolbox/config/mapping_localization_params.yaml` and edit the `initial_state` and `initial_state_covariance` tags from the params file using the values computed previously by the python script.

### 5. Download the segmapping file for your site
The launch file loads segmapping from a fixed path derived from the `maps_site` launch argument (same short name as `mapping_rosbag_manager` search terms, e.g. `MOR`, `LLE`, `USI`):

```
/workspace/maps/maps2d/<maps_site>/segmapping/segmapping_png.yaml
```

Download the segmapping assets for your site into that folder before launching.

Note: Using the [API](REDACTED_API_URL), you can download the segmapping .png file. Save it under the path above and create `segmapping_png.yaml` with values like:
```yaml
image: MOR_OUTDOORS_segmapping_png.png # CHANGE THIS FOR THE ONE YOU DOWNLOADED
mode: trinary
resolution: 0.1
origin: [0.0, 0.0, 0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
```

### 6. GPS constraints (optional)
When `enable_gps_constraints: true` in `mapper_params_online_sync.yaml` (enabled by default), slam_toolbox subscribes to `/odometry/global` and injects GPS pose factors into the Ceres pose graph.

Requirements:
- `solver_plugin` must be `solver_plugins::CeresSolver` (other solvers log a warning and ignore GPS input)

Parameters in `config/mapper_params_online_sync.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_gps_constraints` | `true` | Subscribe to `/odometry/global` and add GPS factors |
| `gps_constraint_every_n_nodes` | `5` | Add a GPS-eligible node every N pose-graph nodes |
| `gps_covariance_threshold` | `0.015` | Skip GPS msgs whose `var_x` or `var_y` exceeds this |
| `gps_covariance_scale` | `1.0` | Scale factor applied to the GPS information matrix |
| `gps_buffer_size` | `200` | Max buffered GPS messages and pending nodes |
| `gps_max_time_delta` | `0.2` | Max \|Δt\| (seconds) to match a GPS msg to a node |

Set `enable_gps_constraints: false` to disable GPS factor injection entirely.

## Mapping
### 1. Launch mapping
```bash
ros2 launch slam_toolbox online_sync_launch_with_local_ekf.py \
  use_sim_time:=true \
  maps_site:=MOR \
  slam_params_file:=/workspace/rover/ros2/src/location/kiwi_slam_toolbox/config/mapper_params_online_sync.yaml
```

Launch arguments:
- `maps_site` — site folder under `/workspace/maps/maps2d/` (default: `LLE`)
- `use_rviz` — set to `false` to skip RViz (default: `true`)

By default this starts RViz with `slam_toolbox_default.rviz`, which shows the segmapping overlay and an `rviz_satellite` AerialMap layer (satellite imagery; uses `/fix` when available for georeferencing).


### 2. Play the rosbag (in another terminal)
In another terminal type the following:
```bash
export ROSBAG_NAME=mor_storage_0
export ROSBAG_FOLDER=/workspace/rosbags/mapping2d/mor
export ROSBAG_PATH=$ROSBAG_FOLDER/$ROSBAG_NAME.mcap 
ros2 bag play $ROSBAG_PATH --remap tf:=tf2 --clock
```
Important: Remember to modify the env. variables for the ones corresponding to your rosbag.

### 3. Edit the initial node
You will notice that the robot poses coming from the EKF taking the accurate GPS measurements, which is represented by the red arrows and the pose computed by slam toolbox (as seen in the blue path) differ. To fix this, it is tipycally enough to rotate the initial node. To fix this:
1. Pause the rosbag (you can do this by hitting space bar in the terminal playing it) after both paths are clearly visible as shown in the image:
   
![Screenshot from 2025-03-27 15-54-29](https://github.com/user-attachments/assets/521565e3-2460-4bbf-819a-86fb597b8729)

3. Activate interactive mode in the checkbox on the rviz panel
4. Rotate the first node from the posegraph by using the interactive marker:

![image](https://github.com/user-attachments/assets/03b33b1c-b475-44df-bdc5-cf33e0fc5488)

6. Click on save changes for the posegraph and map to be updated
7. Tipycally this will result in the posegraph being shifted as well, correct this by moving the first node back to the first robot's pose marked by the first red arrow.
8. Repeat this process multiple times until both paths match as much as possible (see image)

![Screenshot from 2025-03-27 16-02-38](https://github.com/user-attachments/assets/7bca112c-332c-423c-a721-cb71491660bb)

10. Once you feel comfortable with the alignment, uncheck the interactive mode checkbox and continue playing the rosbag

In some cases, moving intermediate nodes is possible, however it is quite challenging due to how slam_toolbox is designed, even when you move the node to the desired location this will only result in small updates of the posegraph.

## Saving the maps
### 1. Save maps
Create a folder. e.g. `/workspace/maps2d/mor`

In another terminal:
```bash
export ROSBAG_NAME=mor_storage_0
export ROSBAG_FOLDER=/workspace/rosbags/mapping2d/mor
export ROSBAG_PATH=$ROSBAG_FOLDER/$ROSBAG_NAME.mcap 

ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph "{filename: /workspace/maps2d/mor/$ROSBAG_NAME}"
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: /workspace/maps2d/mor/$ROSBAG_NAME}}"
```
Important: Remember to modify the env. variables for the ones corresponding to your rosbag.

## Map Edition

### 1. (Optional) Edit offline

Note:By default, this option adds an edge between start and final positions

Edit the config file: `/workspace/rover/ros2/src/location/kiwi_slam_toolbox/config/mapper_params_online_sync_edition.yaml`

Change the field `map_file_name` by the one from the map you want to edit and launch:
```bash
ros2 launch slam_toolbox online_sync_launch_with_local_ekf.py use_sim_time:=false maps_site:=MOR slam_params_file:=/workspace/rover/ros2/src/location/kiwi_slam_toolbox/config/mapper_params_online_sync_edition.yaml
```
This option is still not working well. Fortunately for most cases it does not seem necessary.

### 2. Map merging
1. Execute the map merging launch
```bash
ros2 launch slam_toolbox merge_maps_kinematic_launch.py
```
2. Start adding the maps you want to merge by writting the path without extension e.g. (/workspace/maps2d/mor/mor_campus1_0) and clicking 'add submap' in rviz as shown in the image

![image](https://github.com/user-attachments/assets/74490b37-f7a2-480e-9e15-06bbfccf83a9)

4. Once you've added all the maps, click on 'Generate Map'

![Screenshot from 2025-03-27 17-40-49](https://github.com/user-attachments/assets/fd69bebf-e2b4-4af3-9881-15460784aef8)

3. Save merged map
Save the map by running (Change the path and name of the file to the desired one):
```bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: /workspace/maps2d/mor/mor_final}}"
```

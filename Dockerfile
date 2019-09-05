FROM ros:melodic-ros-base-bionic

# USE BASH
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends apt-utils

# slam_toolbox
RUN mkdir -p catkin_ws/src
RUN cd catkin_ws/src && git clone https://github.com/SteveMacenski/slam_toolbox.git
RUN source /opt/ros/melodic/setup.bash \
    && cd catkin_ws \
    && rosdep update \
    && rosdep install -y -r --from-paths src --ignore-src --rosdistro=melodic -y

RUN apt install python-catkin-tools -y
RUN source /opt/ros/melodic/setup.bash \ 
    && cd catkin_ws/src \
    && catkin_init_workspace \
    && cd .. \
    && catkin build

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <nav_msgs/msg/odometry.hpp>

#include <rclcpp/qos.hpp>
#include <rmw/types.h>

#include "include/System.h"  // Include the SLAM system header

#include "orbslam3_ros2/image_grabber_mono_inertial.hpp"

#include <queue>
#include <mutex>
#include <thread>

#include <tf2_ros/static_transform_broadcaster.h>
#include <geometry_msgs/msg/transform_stamped.hpp>


void publish_static_transform(std::shared_ptr<rclcpp::Node> node)
{
    static tf2_ros::StaticTransformBroadcaster static_broadcaster(node);
    geometry_msgs::msg::TransformStamped static_transform;

    static_transform.header.stamp = node->now();
    static_transform.header.frame_id = "map";
    static_transform.child_frame_id = "odom";
    static_broadcaster.sendTransform(static_transform);
}


int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);

    auto node = std::make_shared<rclcpp::Node>("orbslam3_ros2");

    node->declare_parameter("config_path", "");
    node->declare_parameter("vocab_path", "");

    std::string config_path = node->get_parameter("config_path").as_string();
    std::string vocab_path = node->get_parameter("vocab_path").as_string();

    bool showPangolin = true;
    bool bEqual = false;

    //--------------------------Publishers--------------------------

    auto odom_pub = node->create_publisher<nav_msgs::msg::Odometry>("/slam/odometry", 10);
    auto cloud_pub = node->create_publisher<sensor_msgs::msg::PointCloud2>("/slam/pointcloud", 10);

    publish_static_transform(node);

    // Create SLAM system (IMU_MONOCULAR enables IMU fusion) and ImageGrabberInertial
    auto SLAM = std::make_shared<ORB_SLAM3::System>(vocab_path, config_path, ORB_SLAM3::System::IMU_MONOCULAR, showPangolin);

    auto igb = std::make_shared<ImageGrabberInertial>(SLAM, bEqual, odom_pub, cloud_pub, node, "map");

    // Image subscription
    std::string imgTopicName = "/camera/rgb/image_color";
    auto sub_img0 = node->create_subscription<sensor_msgs::msg::Image>(
        imgTopicName, 5, [igb](const sensor_msgs::msg::Image::SharedPtr msg) { igb->grabImage(msg); });

    // IMU subscription - depth 1000 since IMU publishes much faster than images
    std::string imuTopicName = "/imu";
    auto sub_imu = node->create_subscription<sensor_msgs::msg::Imu>(
        imuTopicName, 1000, [igb](const sensor_msgs::msg::Imu::SharedPtr msg) { igb->grabImu(msg); });

    // Start processing images in a separate thread
    std::thread image_thread(&ImageGrabberInertial::processImages, igb);

    rclcpp::spin(node);
    std::cout << "Node stop to spinning!" << std::endl;

    rclcpp::shutdown();
    image_thread.join();

    return 0;
}

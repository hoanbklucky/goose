#include "orbslam3_ros2/image_grabber_mono_inertial.hpp"
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <Eigen/Core>
#include <fstream>
#include <sophus/se3.hpp>

ImageGrabberInertial::ImageGrabberInertial(std::shared_ptr<ORB_SLAM3::System> pSLAM, bool bClahe,
    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr rospub,
    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_pub,
    std::shared_ptr<rclcpp::Node> ros_node, const std::string camera_frame_name)
    : mpSLAM(pSLAM), mbClahe(bClahe), first_pose(true), odom_pub_(rospub), cloud_pub_(cloud_pub),
      rosNode_(ros_node), tf_frame(camera_frame_name){
        odom_msg_.header.frame_id = tf_frame;
        odom_msg_.child_frame_id = "odom";
    }

void ImageGrabberInertial::grabImage(const sensor_msgs::msg::Image::SharedPtr msg)
{
    std::lock_guard<std::mutex> lock(mBufMutex);
    img0Buf.push(msg);
}

void ImageGrabberInertial::grabImu(const sensor_msgs::msg::Imu::SharedPtr msg)
{
    std::lock_guard<std::mutex> lock(mBufMutexIMU);
    imuBuf.push(msg);
}

cv::Mat ImageGrabberInertial::getImage(const sensor_msgs::msg::Image::SharedPtr &img_msg)
{
    try
    {
        cv::Mat image = cv_bridge::toCvCopy(img_msg, "rgb8")->image;
        if (mbClahe)
        {
            cv::cvtColor(image, image, cv::COLOR_BGR2GRAY);
            mClahe->apply(image, image);
        }
        return image;
    }
    catch (cv_bridge::Exception &e)
    {
        RCLCPP_ERROR(rosNode_->get_logger(), "cv_bridge exception: %s", e.what());
        return cv::Mat();
    }
}

void ImageGrabberInertial::savePoseToFile(const Sophus::SE3f &pose, double sec, double nanosec)
{
    std::ofstream pose_file("pose.txt", std::ios::app);
    if (!pose_file.is_open())
    {
        RCLCPP_ERROR(rosNode_->get_logger(), "Failed to open pose.txt for writing.");
        return;
    }
    Eigen::Matrix4f T = pose.matrix();
    pose_file << sec << "." << nanosec << " ";
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            pose_file << T(i, j) << " ";
    pose_file << std::endl;
    pose_file.close();
}

void ImageGrabberInertial::processImages()
{
    while (rclcpp::ok())
    {
        sensor_msgs::msg::Image::SharedPtr img_msg;
        {
            std::lock_guard<std::mutex> lock(mBufMutex);
            if (img0Buf.empty())
                continue;
            img_msg = img0Buf.front();
            img0Buf.pop();
        }

        cv::Mat image = getImage(img_msg);
        if (image.empty())
            continue;

        double tImage = img_msg->header.stamp.sec + 1e-9 * img_msg->header.stamp.nanosec;

        // Gather all IMU measurements timestamped at or before this frame
        std::vector<ORB_SLAM3::IMU::Point> vImuMeas;
        {
            std::lock_guard<std::mutex> lock(mBufMutexIMU);
            while (!imuBuf.empty())
            {
                auto imu_msg = imuBuf.front();
                double tImu = imu_msg->header.stamp.sec + 1e-9 * imu_msg->header.stamp.nanosec;
                if (tImu > tImage)
                    break;

                cv::Point3f acc(imu_msg->linear_acceleration.x,
                                 imu_msg->linear_acceleration.y,
                                 imu_msg->linear_acceleration.z);
                cv::Point3f gyr(imu_msg->angular_velocity.x,
                                 imu_msg->angular_velocity.y,
                                 imu_msg->angular_velocity.z);
                vImuMeas.push_back(ORB_SLAM3::IMU::Point(acc, gyr, tImu));
                imuBuf.pop();
            }
        }

        if (vImuMeas.empty())
            continue;  // wait until IMU has caught up to this frame's timestamp

        // Track the image with IMU measurements and get the camera pose
        Sophus::SE3f pose = mpSLAM->TrackMonocular(image, tImage, vImuMeas);

        // Get the 3D map points from the SLAM system
        std::vector<ORB_SLAM3::MapPoint*> mapPoints = mpSLAM->GetTrackedMapPoints();

        std::vector<Eigen::Vector3f> point_cloud;
        for (auto p : mapPoints)
        {
            if (p && !p->isBad())
            {
                Eigen::Vector3f pos = p->GetWorldPos();
                point_cloud.emplace_back(pos[0], pos[1], pos[2]);
            }
        }

        publishSE3fToOdom(pose);
        publishPointCloud(point_cloud);
    }
}

void ImageGrabberInertial::publishSE3fToOdom(const Sophus::SE3f& Tcw)
{
    Sophus::SE3f Twc = Tcw.inverse();
    Eigen::Vector3f twc = Twc.translation();
    Eigen::Quaternionf q = Twc.unit_quaternion();

    odom_msg_.pose.pose.position.x = twc.z();
    odom_msg_.pose.pose.position.y = -twc.x();
    odom_msg_.pose.pose.position.z = -twc.y();

    odom_msg_.pose.pose.orientation.x = q.z();
    odom_msg_.pose.pose.orientation.y = -q.x();
    odom_msg_.pose.pose.orientation.z = -q.y();
    odom_msg_.pose.pose.orientation.w = q.w();

    double position_variance = 0.01;
    double orientation_variance = 0.02;

    for (int i = 0; i < 36; i++) odom_msg_.pose.covariance[i] = 0.0;

    odom_msg_.pose.covariance[0] = position_variance;
    odom_msg_.pose.covariance[7] = position_variance;
    odom_msg_.pose.covariance[14] = position_variance;
    odom_msg_.pose.covariance[21] = orientation_variance;
    odom_msg_.pose.covariance[28] = orientation_variance;
    odom_msg_.pose.covariance[35] = orientation_variance;

    odom_msg_.header.stamp = rosNode_->get_clock()->now();
    odom_pub_->publish(odom_msg_);
}

void ImageGrabberInertial::publishPointCloud(const std::vector<Eigen::Vector3f>& points)
{
    sensor_msgs::msg::PointCloud2 cloud_msg;
    cloud_msg.header.frame_id = "map";
    cloud_msg.height = 1;
    cloud_msg.width = points.size();
    cloud_msg.is_dense = false;
    cloud_msg.is_bigendian = false;

    sensor_msgs::PointCloud2Modifier modifier(cloud_msg);
    modifier.setPointCloud2FieldsByString(1, "xyz");
    modifier.resize(points.size());

    sensor_msgs::PointCloud2Iterator<float> iter_x(cloud_msg, "x");
    sensor_msgs::PointCloud2Iterator<float> iter_y(cloud_msg, "y");
    sensor_msgs::PointCloud2Iterator<float> iter_z(cloud_msg, "z");

    for (const auto& point : points)
    {
        *iter_x = point.z();
        *iter_y = -point.x();
        *iter_z = -point.y();
        ++iter_x;
        ++iter_y;
        ++iter_z;
    }
    cloud_msg.header.stamp = rosNode_->get_clock()->now();
    cloud_pub_->publish(cloud_msg);
}

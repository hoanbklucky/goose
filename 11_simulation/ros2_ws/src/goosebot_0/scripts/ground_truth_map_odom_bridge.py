#!/usr/bin/env python3
"""
Publishes the map -> odom transform Nav2 requires, using Gazebo's
ground-truth pose instead of live SLAM.

map->odom = (map->base_link)_groundtruth composed with the inverse of
(odom->base_link)_wheelodom. This keeps localization exact even as wheel
odom drifts, and matches Nav2's expected map/odom/base_link TF chain
without needing AMCL or a saved-map + particle filter.

Quaternion<->matrix math is implemented inline (no tf_transformations /
transforms3d dependency) since the apt-packaged transforms3d build breaks
under NumPy 2.0 (calls the removed np.maximum_sctype).
"""

from collections import deque

import numpy as np
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


def quaternion_matrix(q):
    """q = [x, y, z, w] -> 4x4 homogeneous rotation matrix."""
    x, y, z, w = q
    n = x*x + y*y + z*z + w*w
    if n < 1e-12:
        return np.identity(4)
    s = 2.0 / n
    X, Y, Z = x*s, y*s, z*s
    wX, wY, wZ = w*X, w*Y, w*Z
    xX, xY, xZ = x*X, x*Y, x*Z
    yY, yZ, zZ = y*Y, y*Z, z*Z
    m = np.identity(4)
    m[0, 0] = 1.0 - (yY + zZ); m[0, 1] = xY - wZ;       m[0, 2] = xZ + wY
    m[1, 0] = xY + wZ;         m[1, 1] = 1.0 - (xX + zZ); m[1, 2] = yZ - wX
    m[2, 0] = xZ - wY;         m[2, 1] = yZ + wX;       m[2, 2] = 1.0 - (xX + yY)
    return m


def quaternion_from_matrix(m):
    """3x3 (or 4x4, upper-left 3x3 used) rotation matrix -> [x, y, z, w]."""
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        S = np.sqrt(tr + 1.0) * 2
        w = 0.25 * S
        x = (m[2, 1] - m[1, 2]) / S
        y = (m[0, 2] - m[2, 0]) / S
        z = (m[1, 0] - m[0, 1]) / S
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        S = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / S
        x = 0.25 * S
        y = (m[0, 1] + m[1, 0]) / S
        z = (m[0, 2] + m[2, 0]) / S
    elif m[1, 1] > m[2, 2]:
        S = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / S
        x = (m[0, 1] + m[1, 0]) / S
        y = 0.25 * S
        z = (m[1, 2] + m[2, 1]) / S
    else:
        S = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / S
        x = (m[0, 2] + m[2, 0]) / S
        y = (m[1, 2] + m[2, 1]) / S
        z = 0.25 * S
    return np.array([x, y, z, w])


def pose_to_matrix(pose):
    t = pose.position
    q = pose.orientation
    m = quaternion_matrix([q.x, q.y, q.z, q.w])
    m[0:3, 3] = [t.x, t.y, t.z]
    return m


def stamp_to_sec(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def interpolate_pose_matrix(pose_a, pose_b, alpha):
    """Pose3d interpolation between two geometry_msgs/Pose: linear on
    translation, shortest-path slerp on rotation. Returns a 4x4 matrix."""
    ta = np.array([pose_a.position.x, pose_a.position.y, pose_a.position.z])
    tb = np.array([pose_b.position.x, pose_b.position.y, pose_b.position.z])
    qa = np.array([pose_a.orientation.x, pose_a.orientation.y,
                   pose_a.orientation.z, pose_a.orientation.w])
    qb = np.array([pose_b.orientation.x, pose_b.orientation.y,
                   pose_b.orientation.z, pose_b.orientation.w])
    qa = qa / np.linalg.norm(qa)
    qb = qb / np.linalg.norm(qb)
    d = float(np.dot(qa, qb))
    if d < 0.0:          # take the short way round
        qb = -qb
        d = -d
    if d > 0.9995:       # nearly parallel: nlerp is exact enough
        q = qa + alpha * (qb - qa)
    else:
        th = np.arccos(d)
        q = (np.sin((1.0 - alpha) * th) * qa + np.sin(alpha * th) * qb) / np.sin(th)
    q = q / np.linalg.norm(q)
    m = quaternion_matrix(q)
    m[0:3, 3] = ta + alpha * (tb - ta)
    return m


class GroundTruthMapOdomBridge(Node):
    def __init__(self):
        super().__init__('ground_truth_map_odom_bridge')
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        # Time-matched pairing (see _process_pending): keep a short history of
        # EKF outputs and interpolate to each ground-truth stamp, instead of
        # pairing a GT sample with whatever EKF sample arrived last.
        self.odom_buf = deque(maxlen=120)
        self.pending_gt = deque(maxlen=30)
        # Must match whatever is ACTUALLY broadcasting odom->base_footprint
        # right now, not just whichever odom source happens to exist. As of
        # Step 6/7, that's the EKF's fused output -- not the raw open-loop
        # /odom_cmdvel. Inverting the wrong odom here silently decouples
        # this node's correction from what's really on the TF tree: the two
        # heading estimates (this one's stale open-loop yaw vs. the EKF's
        # IMU-corrected yaw) drift apart, and every new ground-truth message
        # reapplies a correction based on the wrong one -- visible as a fast
        # back-and-forth yaw jitter on the robot marker in RViz even though
        # the map/costmap stay rock solid. Revisit again at Step 8, when
        # this whole node retires in favor of navsat_transform_node + a
        # global EKF owning map->odom instead.
        self.create_subscription(Odometry, '/odometry/filtered', self.odom_cb, 10)
        self.create_subscription(Odometry, '/ground_truth/pose', self.gt_cb, 10)

        # Temporary debug visibility: this node has no other log output, so
        # a silent failure and a silent success have looked identical from
        # outside. Remove once map->odom is confirmed stable.
        self._logged_first_odom = False
        self._logged_first_gt = False
        self._logged_first_tf = False
        self.get_logger().info(
            'ground_truth_map_odom_bridge started; waiting for both '
            '/odometry/filtered and /ground_truth/pose before publishing map->odom.'
        )

    def odom_cb(self, msg: Odometry):
        self.odom_buf.append(msg)
        if not self._logged_first_odom:
            self._logged_first_odom = True
            self.get_logger().info('Received first /odometry/filtered message.')
        self._process_pending()

    def gt_cb(self, msg: Odometry):
        if not self._logged_first_gt:
            self._logged_first_gt = True
            self.get_logger().info('Received first /ground_truth/pose message.')
        self.pending_gt.append(msg)
        self._process_pending()

    def _odom_matrix_at(self, t):
        """odom->base_footprint matrix interpolated to time t (seconds).
        Returns None if t is newer than the newest EKF sample (caller should
        wait) and False if t is older than everything buffered (drop)."""
        buf = self.odom_buf
        if not buf:
            return None
        t_new = stamp_to_sec(buf[-1].header.stamp)
        t_old = stamp_to_sec(buf[0].header.stamp)
        if t > t_new:
            return None
        if t < t_old:
            return False
        prev = buf[0]
        for cur in buf:
            t_cur = stamp_to_sec(cur.header.stamp)
            if t_cur >= t:
                t_prev = stamp_to_sec(prev.header.stamp)
                if t_cur - t_prev < 1e-9:
                    return pose_to_matrix(cur.pose.pose)
                alpha = (t - t_prev) / (t_cur - t_prev)
                return interpolate_pose_matrix(prev.pose.pose, cur.pose.pose,
                                               min(max(alpha, 0.0), 1.0))
            prev = cur
        return pose_to_matrix(buf[-1].pose.pose)

    def _process_pending(self):
        while self.pending_gt:
            gt = self.pending_gt[0]
            odom_to_base = self._odom_matrix_at(stamp_to_sec(gt.header.stamp))
            if odom_to_base is None:
                # GT is newer than the newest EKF output; wait for the next
                # /odometry/filtered message (<= one EKF period, ~33 ms).
                if not self.odom_buf:
                    self.get_logger().warn(
                        'Got /ground_truth/pose but no /odometry/filtered yet -- '
                        'not publishing map->odom.', throttle_duration_sec=2.0)
                return
            self.pending_gt.popleft()
            if odom_to_base is False:
                continue  # GT sample older than our history; discard it
            self._publish_map_to_odom(gt, odom_to_base)

    def _publish_map_to_odom(self, msg: Odometry, odom_to_base):
        try:
            map_to_base = pose_to_matrix(msg.pose.pose)
            map_to_odom = map_to_base @ np.linalg.inv(odom_to_base)

            trans = map_to_odom[0:3, 3]
            quat = quaternion_from_matrix(map_to_odom[0:3, 0:3])
        except Exception as e:
            self.get_logger().error(f'Failed to compute map->odom: {e}', throttle_duration_sec=2.0)
            return

        tf_msg = TransformStamped()
        tf_msg.header.stamp = msg.header.stamp
        tf_msg.header.frame_id = 'map'
        tf_msg.child_frame_id = 'odom'
        tf_msg.transform.translation.x = float(trans[0])
        tf_msg.transform.translation.y = float(trans[1])
        tf_msg.transform.translation.z = float(trans[2])
        tf_msg.transform.rotation.x = float(quat[0])
        tf_msg.transform.rotation.y = float(quat[1])
        tf_msg.transform.rotation.z = float(quat[2])
        tf_msg.transform.rotation.w = float(quat[3])
        self.tf_broadcaster.sendTransform(tf_msg)
        if not self._logged_first_tf:
            self._logged_first_tf = True
            self.get_logger().info('Published first map->odom transform.')


def main():
    rclpy.init()
    node = GroundTruthMapOdomBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

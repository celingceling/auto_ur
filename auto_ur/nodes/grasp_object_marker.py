"""Publish a visual-only grasp object marker for the gripper demo."""

import json

from auto_ur.config import ConfigLoader


def main() -> None:
    """Publish an object marker that follows playback events."""
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String
    from visualization_msgs.msg import Marker

    class GraspObjectMarker(Node):
        """Animate a marker object through visual grasp states."""

        def __init__(self) -> None:
            super().__init__('auto_ur_grasp_object_marker')
            loader = ConfigLoader()
            poses = loader.load_named_cartesian_poses()[
                'named_cartesian_poses'
            ]
            end_effector = loader.load_yaml(
                'end_effectors/robotiq_2f_85.yaml'
            )['end_effector']
            self._pick_pose = poses['pick']
            self._place_pose = poses['place']
            self._attach_frame = end_effector.get(
                'object_attach_frame',
                'tool0',
            )
            self._state = 'pick'

            qos = QoSProfile(depth=1)
            qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
            qos.reliability = ReliabilityPolicy.RELIABLE
            self._publisher = self.create_publisher(
                Marker,
                '/auto_ur/gripper_object/object_marker',
                qos,
            )
            self.create_subscription(
                String,
                '/auto_ur/gripper_object/playback_event',
                self._handle_event,
                10,
            )
            self._timer = self.create_timer(0.1, self._publish)
            self._publish()

        def _handle_event(self, message: String) -> None:
            try:
                payload = json.loads(message.data)
            except json.JSONDecodeError:
                return

            event = payload.get('event')
            label = payload.get('label')
            if event == 'START' and label == 'gripper_object_demo:pre_pick':
                self._state = 'pick'
            elif event == 'START' and label == 'gripper_object_demo:lift':
                self._state = 'attached'
            elif event == 'END' and label == 'gripper_object_demo:place':
                self._state = 'placed'

        def _publish(self) -> None:
            marker = Marker()
            marker.header.stamp.sec = 0
            marker.header.stamp.nanosec = 0
            marker.ns = 'auto_ur_gripper_object'
            marker.id = 1
            marker.type = Marker.CUBE
            marker.action = Marker.ADD
            marker.scale.x = 0.07
            marker.scale.y = 0.07
            marker.scale.z = 0.07
            marker.color.r = 1.0
            marker.color.g = 0.42
            marker.color.b = 0.08
            marker.color.a = 1.0
            marker.pose.orientation.w = 1.0

            if self._state == 'attached':
                marker.header.frame_id = self._attach_frame
                marker.pose.position.z = 0.10
            elif self._state == 'placed':
                self._set_pose(marker, self._place_pose)
            else:
                self._set_pose(marker, self._pick_pose)

            self._publisher.publish(marker)

        def _set_pose(self, marker: Marker, pose: dict) -> None:
            marker.header.frame_id = pose.get('frame_id', 'base_link')
            position = pose.get('position', {})
            marker.pose.position.x = float(position.get('x', 0.0))
            marker.pose.position.y = float(position.get('y', 0.0))
            marker.pose.position.z = float(position.get('z', 0.0))

    rclpy.init()
    node = GraspObjectMarker()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

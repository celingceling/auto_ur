"""Publish a simple floor marker for the RViz demo."""


def main() -> None:
    """Publish a low-profile floor plane in the robot base frame."""
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from visualization_msgs.msg import Marker

    class FloorMarkerPublisher(Node):
        """Publish a transient floor marker for RViz."""

        def __init__(self) -> None:
            super().__init__('auto_ur_floor_marker_publisher')
            qos = QoSProfile(depth=1)
            qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
            qos.reliability = ReliabilityPolicy.RELIABLE
            self._publisher = self.create_publisher(
                Marker,
                '/auto_ur/floor_marker',
                qos,
            )
            self._timer = self.create_timer(1.0, self._publish)
            self._publish()

        def _publish(self) -> None:
            marker = Marker()
            marker.header.frame_id = 'base_link'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'auto_ur_demo'
            marker.id = 1
            marker.type = Marker.CUBE
            marker.action = Marker.ADD
            marker.pose.position.x = 0.0
            marker.pose.position.y = 0.0
            marker.pose.position.z = -0.015
            marker.pose.orientation.w = 1.0
            marker.scale.x = 1.2
            marker.scale.y = 1.2
            marker.scale.z = 0.02
            marker.color.r = 0.18
            marker.color.g = 0.18
            marker.color.b = 0.18
            marker.color.a = 1.0
            self._publisher.publish(marker)

    rclpy.init()
    node = FloorMarkerPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

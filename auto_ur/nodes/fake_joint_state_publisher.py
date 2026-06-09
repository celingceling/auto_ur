"""Publish a static UR10e joint state for standalone plan-only demos."""

from auto_ur.config import ConfigLoader


def main() -> None:
    """Publish named UR10e joint positions on /joint_states."""
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState

    class FakeJointStatePublisher(Node):
        """Small /joint_states source for plan-only MoveItPy startup."""

        def __init__(self) -> None:
            super().__init__('auto_ur_fake_joint_state_publisher')
            loader = ConfigLoader()
            robot = loader.load_robot('ur10e')['robot']
            named_states = loader.load_named_joint_states('ur10e')[
                'named_joint_states'
            ]
            start_state = named_states.get('demo_start', named_states['ready'])
            self._joint_names = robot['joint_names']
            self._positions = [
                float(start_state.get(joint_name, 0.0))
                for joint_name in self._joint_names
            ]
            self._publisher = self.create_publisher(JointState, 'joint_states', 10)
            self._timer = self.create_timer(1.0 / 30.0, self._publish)
            self._publish()

        def _publish(self) -> None:
            message = JointState()
            message.header.stamp = self.get_clock().now().to_msg()
            message.name = self._joint_names
            message.position = self._positions
            self._publisher.publish(message)

    rclpy.init()
    node = FakeJointStatePublisher()
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

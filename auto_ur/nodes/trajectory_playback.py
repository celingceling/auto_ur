"""Replay planned trajectories as joint states for RViz demos."""

from collections import deque
from copy import deepcopy

from auto_ur.config import ConfigLoader


def main() -> None:
    """Animate received JointTrajectory messages as demo joint states."""
    import rclpy
    from rclpy.duration import Duration
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from trajectory_msgs.msg import JointTrajectory

    class TrajectoryPlayback(Node):
        """Queue planned trajectories and publish interpolated joint states."""

        def __init__(self) -> None:
            super().__init__('auto_ur_trajectory_playback')
            loader = ConfigLoader()
            robot = loader.load_robot('ur10e')['robot']
            named_states = loader.load_named_joint_states('ur10e')[
                'named_joint_states'
            ]
            start_state = named_states.get('demo_start', named_states['ready'])
            self._time_scale = max(
                0.1,
                float(self.declare_parameter('time_scale', 2.0).value),
            )
            self._hold_duration = max(
                0.0,
                float(self.declare_parameter('hold_duration', 2.0).value),
            )
            self._joint_names = robot['joint_names']
            self._positions = [
                float(start_state.get(joint_name, 0.0))
                for joint_name in self._joint_names
            ]
            self._queue = deque()
            self._active = None
            self._active_label = None
            self._active_started_at = None
            self._hold_until = None
            self._demo_publisher = self.create_publisher(
                JointState,
                '/auto_ur/joint_states',
                10,
            )
            self._global_publisher = self.create_publisher(
                JointState,
                '/joint_states',
                10,
            )
            self.create_subscription(
                JointTrajectory,
                'auto_ur/planned_joint_trajectory',
                self._enqueue,
                10,
            )
            self._timer = self.create_timer(1.0 / 30.0, self._tick)
            self._publish()

        def _enqueue(self, trajectory: JointTrajectory) -> None:
            if not trajectory.joint_names or not trajectory.points:
                return
            self._queue.append(trajectory)
            self.get_logger().info(
                f'Queued trajectory with {len(trajectory.points)} points'
            )

        def _tick(self) -> None:
            now = self.get_clock().now()
            if self._hold_until is not None:
                if now < self._hold_until:
                    self._publish()
                    return
                self._hold_until = None

            if self._active is None and self._queue:
                self._active = self._trajectory_from_current_state(
                    self._queue.popleft()
                )
                self._active_label = _label_for(self._active)
                self._active_started_at = now
                self.get_logger().info(
                    f'START trajectory: {self._active_label}'
                )

            if self._active is not None:
                finished = self._update_from_active(now)
                if finished:
                    self.get_logger().info(
                        f'END trajectory: {self._active_label}'
                    )
                    self._active = None
                    self._active_label = None
                    self._active_started_at = None
                    self._hold_until = now + Duration(
                        seconds=self._hold_duration
                    )

            self._publish()

        def _update_from_active(self, now: object) -> bool:
            elapsed = (
                (now - self._active_started_at).nanoseconds / 1e9
            ) / self._time_scale
            points = self._active.points
            if len(points) == 1:
                self._positions = self._positions_for(points[0].positions)
                return True

            first_time = _seconds_from_duration(points[0].time_from_start)
            if elapsed <= first_time:
                self._positions = self._positions_for(points[0].positions)
                return False

            for index in range(1, len(points)):
                previous = points[index - 1]
                current = points[index]
                previous_time = _seconds_from_duration(previous.time_from_start)
                current_time = _seconds_from_duration(current.time_from_start)
                if elapsed <= current_time:
                    span = max(current_time - previous_time, 1e-6)
                    ratio = (elapsed - previous_time) / span
                    positions = [
                        start + ((end - start) * ratio)
                        for start, end in zip(previous.positions, current.positions)
                    ]
                    self._positions = self._positions_for(positions)
                    return False

            self._positions = self._positions_for(points[-1].positions)
            return True

        def _positions_for(self, trajectory_positions: object) -> list[float]:
            by_name = dict(zip(self._active.joint_names, trajectory_positions))
            return [
                float(by_name.get(joint_name, current))
                for joint_name, current in zip(self._joint_names, self._positions)
            ]

        def _trajectory_from_current_state(
            self,
            trajectory: JointTrajectory,
        ) -> JointTrajectory:
            """Start every replay segment from the current visual state."""
            replay = deepcopy(trajectory)
            current_by_name = dict(zip(self._joint_names, self._positions))
            replay.points[0].positions = [
                float(current_by_name.get(joint_name, position))
                for joint_name, position in zip(
                    replay.joint_names,
                    replay.points[0].positions,
                )
            ]
            replay.points[0].velocities = []
            replay.points[0].accelerations = []
            return replay

        def _publish(self) -> None:
            message = JointState()
            message.header.stamp = self.get_clock().now().to_msg()
            message.name = self._joint_names
            message.position = self._positions
            self._demo_publisher.publish(message)
            self._global_publisher.publish(message)

    def _seconds_from_duration(duration: object) -> float:
        return float(duration.sec) + (float(duration.nanosec) / 1e9)

    def _label_for(trajectory: JointTrajectory) -> str:
        label = trajectory.header.frame_id.strip()
        if label:
            return label
        return 'unlabeled_trajectory'

    rclpy.init()
    node = TrajectoryPlayback()
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

"""Replay arm trajectories with visual Robotiq gripper joint states."""

from collections import deque
from copy import deepcopy
import json

from auto_ur.config import ConfigLoader


def main() -> None:
    """Animate planned gripper demo trajectories for RViz."""
    import rclpy
    from rclpy.duration import Duration
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from std_msgs.msg import String
    from trajectory_msgs.msg import JointTrajectory

    class GripperObjectPlayback(Node):
        """Queue arm plans and publish arm plus gripper joint states."""

        def __init__(self) -> None:
            super().__init__('auto_ur_gripper_object_playback')
            loader = ConfigLoader()
            robot = loader.load_robot('ur10e')['robot']
            named_states = loader.load_named_joint_states('ur10e')[
                'named_joint_states'
            ]
            end_effector = loader.load_yaml(
                'end_effectors/robotiq_2f_85.yaml'
            )['end_effector']
            start_state = named_states.get('demo_start', named_states['ready'])

            self._time_scale = max(
                0.1,
                float(self.declare_parameter('time_scale', 2.0).value),
            )
            self._hold_duration = max(
                0.0,
                float(self.declare_parameter('hold_duration', 2.0).value),
            )
            self._arm_joint_names = robot['joint_names']
            self._arm_positions = [
                float(start_state.get(joint_name, 0.0))
                for joint_name in self._arm_joint_names
            ]
            self._gripper_multipliers = {
                str(joint_name): float(multiplier)
                for joint_name, multiplier
                in end_effector['joints'].items()
            }
            self._gripper_joint_names = list(self._gripper_multipliers)
            self._gripper_open = float(end_effector['open_position'])
            self._gripper_closed = float(end_effector['closed_position'])
            self._gripper_position = self._gripper_open
            self._gripper_transition = None

            self._queue = deque()
            self._active = None
            self._active_label = None
            self._active_started_at = None
            self._hold_until = None
            self._demo_publisher = self.create_publisher(
                JointState,
                '/auto_ur/gripper_object/joint_states',
                10,
            )
            self._global_publisher = self.create_publisher(
                JointState,
                '/joint_states',
                10,
            )
            self._event_publisher = self.create_publisher(
                String,
                '/auto_ur/gripper_object/playback_event',
                10,
            )
            self.create_subscription(
                JointTrajectory,
                '/auto_ur/gripper_object/planned_joint_trajectory',
                self._enqueue,
                10,
            )
            self._timer = self.create_timer(1.0 / 30.0, self._tick)
            self._publish_joint_state()

        def _enqueue(self, trajectory: JointTrajectory) -> None:
            if not trajectory.joint_names or not trajectory.points:
                return
            self._queue.append(trajectory)
            self.get_logger().info(
                f'Queued trajectory with {len(trajectory.points)} points'
            )

        def _tick(self) -> None:
            now = self.get_clock().now()
            self._update_gripper_transition(now)
            if self._hold_until is not None:
                if now < self._hold_until:
                    self._publish_joint_state()
                    return
                self._hold_until = None

            if self._active is None and self._queue:
                self._active = self._trajectory_from_current_state(
                    self._queue.popleft()
                )
                self._active_label = _label_for(self._active)
                self._active_started_at = now
                self._publish_event('START', self._active_label)
                self.get_logger().info(
                    f'START trajectory: {self._active_label}'
                )

            if self._active is not None:
                finished = self._update_from_active(now)
                if finished:
                    label = self._active_label
                    self._publish_event('END', label)
                    self.get_logger().info(f'END trajectory: {label}')
                    self._start_gripper_transition(label, now)
                    self._active = None
                    self._active_label = None
                    self._active_started_at = None
                    self._hold_until = now + Duration(
                        seconds=self._hold_duration
                    )

            self._publish_joint_state()

        def _update_from_active(self, now: object) -> bool:
            elapsed = (
                (now - self._active_started_at).nanoseconds / 1e9
            ) / self._time_scale
            points = self._active.points
            if len(points) == 1:
                self._arm_positions = self._positions_for(points[0].positions)
                return True

            first_time = _seconds_from_duration(points[0].time_from_start)
            if elapsed <= first_time:
                self._arm_positions = self._positions_for(points[0].positions)
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
                    self._arm_positions = self._positions_for(positions)
                    return False

            self._arm_positions = self._positions_for(points[-1].positions)
            return True

        def _positions_for(self, trajectory_positions: object) -> list[float]:
            by_name = dict(zip(self._active.joint_names, trajectory_positions))
            return [
                float(by_name.get(joint_name, current))
                for joint_name, current
                in zip(self._arm_joint_names, self._arm_positions)
            ]

        def _trajectory_from_current_state(
            self,
            trajectory: JointTrajectory,
        ) -> JointTrajectory:
            """Start replay from the current visual arm state."""
            replay = deepcopy(trajectory)
            current_by_name = dict(zip(self._arm_joint_names, self._arm_positions))
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

        def _start_gripper_transition(self, label: str, now: object) -> None:
            if label == 'gripper_object_demo:pick':
                target = self._gripper_closed
            elif label == 'gripper_object_demo:place':
                target = self._gripper_open
            else:
                return

            self._gripper_transition = {
                'start_time': now,
                'duration': max(self._hold_duration, 1e-6),
                'start': self._gripper_position,
                'target': target,
            }

        def _update_gripper_transition(self, now: object) -> None:
            if self._gripper_transition is None:
                return

            transition = self._gripper_transition
            elapsed = (
                now - transition['start_time']
            ).nanoseconds / 1e9
            ratio = min(max(elapsed / transition['duration'], 0.0), 1.0)
            start = transition['start']
            target = transition['target']
            self._gripper_position = start + ((target - start) * ratio)
            if ratio >= 1.0:
                self._gripper_transition = None

        def _publish_joint_state(self) -> None:
            message = JointState()
            message.header.stamp = self.get_clock().now().to_msg()
            message.name = (
                self._arm_joint_names +
                self._gripper_joint_names
            )
            message.position = (
                self._arm_positions +
                [
                    self._gripper_position * multiplier
                    for multiplier in self._gripper_multipliers.values()
                ]
            )
            self._demo_publisher.publish(message)
            self._global_publisher.publish(message)

        def _publish_event(self, event: str, label: str) -> None:
            message = String()
            message.data = json.dumps({
                'event': event,
                'label': label,
            })
            self._event_publisher.publish(message)

    def _seconds_from_duration(duration: object) -> float:
        return float(duration.sec) + (float(duration.nanosec) / 1e9)

    def _label_for(trajectory: JointTrajectory) -> str:
        label = trajectory.header.frame_id.strip()
        if label:
            return label
        return 'unlabeled_trajectory'

    rclpy.init()
    node = GripperObjectPlayback()
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

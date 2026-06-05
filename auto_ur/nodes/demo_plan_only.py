"""MoveItPy plan-only UR10e demo node."""

from typing import Any

from auto_ur import primitives as prims
from auto_ur.config import ConfigLoader
from auto_ur.registry.default_actions import build_default_registry
from auto_ur.skills import pick_and_place_demo


def main() -> None:
    """Run the UR10e plan-only MoveItPy demo."""
    import rclpy
    from moveit.planning import MoveItPy
    from rclpy.logging import get_logger

    rclpy.init()
    logger = get_logger('auto_ur_demo_plan_only')

    try:
        loader = ConfigLoader()
        robot_config = loader.load_robot('ur10e')
        demo_config = loader.load_demo('ur10e_plan_only_demo')
        robot = robot_config['robot']
        demo = demo_config['demo']
        planning_group = robot.get('planning_group', 'ur_manipulator')
        tool_frame = robot.get('tool_frame', 'tool0')

        moveit = MoveItPy(node_name='auto_ur_demo_plan_only')
        moveit.planning_group = planning_group
        arm = moveit.get_planning_component(planning_group)
        robot_model = moveit.get_robot_model()
        reg = build_default_registry()

        logger.info('Registered actions: ' + ', '.join(reg.names()))
        for result in _run_sequence(
            demo.get('sequence', []),
            moveit,
            arm,
            robot_model,
            loader,
            tool_frame,
        ):
            action_name = result.data.get('action_name')
            logger.info(
                f'{action_name}: '
                f'{result.success} - {result.message}'
            )
    finally:
        rclpy.shutdown()


def _run_sequence(sequence: list[dict[str, Any]], moveit: Any, arm: Any,
                  robot_model: Any, loader: ConfigLoader,
                  tool_frame: str) -> list[Any]:
    """Run the configured plan-only demo sequence."""
    results = []
    joint_states = loader.load_named_joint_states('ur10e').get(
        'named_joint_states',
        {},
    )
    cartesian_poses = loader.load_named_cartesian_poses().get(
        'named_cartesian_poses',
        {},
    )

    for step in sequence:
        action = step.get('action')
        if action == 'move_to_named_pose':
            result = prims.move_to_named_pose(
                moveit,
                arm,
                robot_model,
                loader,
                step['pose_name'],
            )
        elif action == 'move_to_joint_state':
            result = prims.move_to_joint_state(
                moveit,
                arm,
                robot_model,
                joint_states[step['joint_state_name']],
            )
        elif action == 'move_to_pose':
            result = prims.move_to_pose(
                arm,
                cartesian_poses[step['pose_name']],
                tool_frame,
            )
        elif action == 'pick_and_place_demo':
            result = pick_and_place_demo(
                arm,
                loader,
                step.get('pick_pose_name', 'pick'),
                step.get('place_pose_name', 'place'),
                tool_frame,
            )
        else:
            raise ValueError(f'Unknown demo action: {action}')
        results.append(result)
    return results


if __name__ == '__main__':
    main()

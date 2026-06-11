"""Action catalog for demo primitives and skills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from typing import Type

from auto_ur.core import ActionSpec
from auto_ur.skills.base import Skill


@dataclass(frozen=True)
class RegisteredAction:
    """Bind action metadata to an optional callable."""

    spec: ActionSpec
    handler: Callable[..., Any] | None = None
    skill_class: Type[Skill] | None = None


class ActionRegistry:
    """Catalog available demo actions."""

    def __init__(self):
        """Create an empty action registry."""
        self._actions: dict[str, RegisteredAction] = {}

    def register(self, spec: ActionSpec,
                 handler: Callable[..., Any] | None = None,
                 skill_class: Type[Skill] | None = None) -> None:
        """Register an action specification and optional callable."""
        if spec.name in self._actions:
            raise ValueError(f'Action already registered: {spec.name}')
        self._actions[spec.name] = RegisteredAction(
            spec=spec,
            handler=handler,
            skill_class=skill_class,
        )

    def register_skill(self, skill_class: Type[Skill],
                       spec: ActionSpec | None = None) -> None:
        """Register a skill class by name for planner instantiation."""
        action_spec = spec or ActionSpec(
            name=skill_class.name,
            tier='skill',
            description=f'{skill_class.name} skill.',
        )
        self.register(action_spec, skill_class=skill_class)

    def get(self, name: str) -> RegisteredAction:
        """Return a registered action by name."""
        try:
            return self._actions[name]
        except KeyError as exc:
            raise KeyError(f'Unknown action: {name}') from exc

    def list(self) -> list[ActionSpec]:  # noqa: A003
        """Return registered action specs in registration order."""
        return [registered.spec for registered in self._actions.values()]

    def names(self) -> list[str]:
        """Return registered action names in registration order."""
        return list(self._actions.keys())

    def instantiate(self, action: dict[str, Any]) -> Skill:
        """Instantiate a registered skill from an action dictionary."""
        skill_name = action.get('skill') or action.get('action')
        if not skill_name:
            raise ValueError(
                'Action dictionary requires a skill or action key',
            )
        registered = self.get(skill_name)
        if registered.skill_class is None:
            raise ValueError(f'Action is not instantiable skill: {skill_name}')
        params = action.get('params', {})
        if not isinstance(params, dict):
            raise ValueError('Action params must be a dictionary')
        return registered.skill_class(**params)

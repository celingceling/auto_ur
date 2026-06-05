"""Action catalog for demo primitives and skills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from autoUR.core import ActionSpec


@dataclass(frozen=True)
class RegisteredAction:
    """Bind action metadata to an optional callable."""

    spec: ActionSpec
    handler: Callable[..., Any] | None = None


class ActionRegistry:
    """Catalog available demo actions."""

    def __init__(self):
        """Create an empty action registry."""
        self._actions: dict[str, RegisteredAction] = {}

    def register(self, spec: ActionSpec,
                 handler: Callable[..., Any] | None = None) -> None:
        """Register an action specification and optional callable."""
        if spec.name in self._actions:
            raise ValueError(f'Action already registered: {spec.name}')
        self._actions[spec.name] = RegisteredAction(spec=spec, handler=handler)

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

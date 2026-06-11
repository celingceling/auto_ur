"""Structured result contracts for primitives, skills, and recovery hooks."""

from dataclasses import dataclass, field
from typing import Any

from auto_ur.core.failures import Failure
from auto_ur.core.failures import FailureType


@dataclass
class PrimitiveResult:
    """Represent the outcome of a low-level robot or perception primitive."""

    success: bool
    message: str = ''
    error_code: FailureType | str | None = None
    failure: Failure | None = None
    details: dict[str, Any] = field(default_factory=dict)
    world_updates: dict[str, Any] = field(default_factory=dict)

    @property
    def data(self) -> dict[str, Any]:
        """Compatibility alias for older demo code."""
        return self.details

    @data.setter
    def data(self, value: dict[str, Any]) -> None:
        self.details = value


@dataclass
class SkillResult:
    """Represent the outcome of a reusable robot skill."""

    success: bool
    message: str = ''
    failure: Failure | None = None
    details: dict[str, Any] = field(default_factory=dict)
    world_updates: dict[str, Any] = field(default_factory=dict)

    @property
    def data(self) -> dict[str, Any]:
        """Compatibility alias for older demo code."""
        return self.details

    @data.setter
    def data(self, value: dict[str, Any]) -> None:
        self.details = value


@dataclass
class RecoveryResult:
    """Represent the outcome of bounded local recovery inside a skill."""

    success: bool
    message: str = ''
    failure: Failure | None = None
    details: dict[str, Any] = field(default_factory=dict)
    world_updates: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult(PrimitiveResult):
    """Backward-compatible primitive result name for existing callers."""

    def __init__(self, success: bool, message: str = '',
                 data: dict[str, Any] | None = None,
                 error_code: FailureType | str | None = None,
                 failure: Failure | None = None,
                 details: dict[str, Any] | None = None,
                 world_updates: dict[str, Any] | None = None):
        """Create a result while accepting the historical ``data`` keyword."""
        super().__init__(
            success=success,
            message=message,
            error_code=error_code,
            failure=failure,
            details=details if details is not None else data or {},
            world_updates=world_updates or {},
        )

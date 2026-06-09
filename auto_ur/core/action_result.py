"""Standard result contract for future robot actions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    """Represent the outcome of a plan-only action."""

    success: bool
    message: str = ''
    data: dict[str, Any] = field(default_factory=dict)

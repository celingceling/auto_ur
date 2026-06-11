"""Action metadata contract for primitives, skills, and tasks."""

from dataclasses import dataclass, field


@dataclass
class ActionSpec:
    """Describe a future robot action without implementing execution."""

    name: str
    tier: str
    description: str
    required_inputs: list[str] = field(default_factory=list)
    optional_inputs: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    safety_checks: list[str] = field(default_factory=list)
    supports_dry_run: bool = False
    supports_plan_only: bool = False

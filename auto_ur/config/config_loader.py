"""YAML configuration loader for the auto_ur demo package."""

from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """Load YAML configuration from the source tree or installed package."""

    def __init__(self, package_name: str = 'auto_ur',
                 config_root: Path | None = None):
        """Create a loader for package configuration files."""
        self.package_name = package_name
        self.config_root = config_root or self._default_config_root()

    def load_yaml(self, relative_path: str) -> dict[str, Any]:
        """Load a YAML file relative to the package config directory."""
        config_path = self.config_root / relative_path
        with config_path.open('r', encoding='utf-8') as config_file:
            loaded_config = yaml.safe_load(config_file)

        if not isinstance(loaded_config, dict):
            raise ValueError(f'Config file must contain a mapping: {config_path}')
        return loaded_config

    def load_robot(self, robot_name: str = 'ur10e') -> dict[str, Any]:
        """Load a robot configuration by robot name."""
        return self.load_yaml(f'robots/{robot_name}.yaml')

    def load_named_joint_states(self,
                                robot_name: str = 'ur10e') -> dict[str, Any]:
        """Load named joint states for a robot."""
        return self.load_yaml(f'poses/named_joint_states_{robot_name}.yaml')

    def load_named_cartesian_poses(self) -> dict[str, Any]:
        """Load named task-space poses."""
        return self.load_yaml('poses/named_cartesian_poses.yaml')

    def load_demo(self,
                  demo_name: str = 'ur10e_plan_only_demo') -> dict[str, Any]:
        """Load a demo sequence configuration."""
        return self.load_yaml(f'demos/{demo_name}.yaml')

    def load_safety(self,
                    safety_name: str = 'default_motion_limits') -> dict[str, Any]:
        """Load safety settings."""
        return self.load_yaml(f'safety/{safety_name}.yaml')

    def _default_config_root(self) -> Path:
        """Resolve config root from package share or local source tree."""
        try:
            from ament_index_python.packages import get_package_share_directory

            package_share = Path(get_package_share_directory(self.package_name))
            installed_config = package_share / 'config'
            if installed_config.exists():
                return installed_config
        except Exception:
            pass

        return Path(__file__).resolve().parents[2] / 'config'

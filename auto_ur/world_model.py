"""Symbolic world state used by reusable manipulation skills."""

from copy import deepcopy
from typing import Any


class WorldModel:
    """Store symbolic object, location, and robot state."""

    def __init__(self, objects: dict[str, dict[str, Any]] | None = None,
                 locations: dict[str, dict[str, Any]] | None = None,
                 robot: dict[str, Any] | None = None):
        """Create a dictionary-backed world model."""
        self.objects = deepcopy(objects or {})
        self.locations = deepcopy(locations or {})
        self.robot = {
            'holding': None,
            'hand_empty': True,
            'gripper_ready': True,
        }
        self.robot.update(deepcopy(robot or {}))

    def object_exists(self, object_id: str) -> bool:
        """Return whether an object is known to the world."""
        return object_id in self.objects

    def pose_known(self, entity_id: str) -> bool:
        """Return whether an object or location has a pose."""
        entity = self._entity(entity_id)
        return bool(entity and entity.get('pose') is not None)

    def confidence_above(self, entity_id: str, threshold: float) -> bool:
        """Return whether perception confidence is above a threshold."""
        entity = self._entity(entity_id)
        if entity is None:
            return False
        return float(entity.get('confidence', 1.0)) >= threshold

    def object_reachable(self, object_id: str) -> bool:
        """Return whether an object is currently considered reachable."""
        return bool(self.objects.get(object_id, {}).get('reachable', False))

    def location_reachable(self, location_id: str) -> bool:
        """Return whether a location is currently considered reachable."""
        return bool(
            self.locations.get(location_id, {}).get('reachable', False),
        )

    def location_clear(self, location_id: str) -> bool:
        """Return whether a location is clear for placement."""
        return bool(self.locations.get(location_id, {}).get('clear', False))

    def hand_empty(self) -> bool:
        """Return whether the robot hand is empty."""
        return bool(self.robot.get('hand_empty', False))

    def gripper_ready(self) -> bool:
        """Return whether the gripper is ready for manipulation."""
        return bool(self.robot.get('gripper_ready', False))

    def holding(self, object_id: str) -> bool:
        """Return whether the robot is holding a specific object."""
        return self.robot.get('holding') == object_id

    def update_robot_holding(self, object_id: str | None) -> None:
        """Update robot holding and hand-empty state."""
        self.robot['holding'] = object_id
        self.robot['hand_empty'] = object_id is None

    def update_object_location(self, object_id: str, location_id: str) -> None:
        """Record that an object is at a symbolic location."""
        self.objects.setdefault(object_id, {})['location'] = location_id
        self.objects[object_id]['state'] = f'at:{location_id}'
        if location_id in self.locations:
            self.locations[location_id]['clear'] = False

    def apply_updates(self, updates: dict[str, Any] | None) -> None:
        """Apply structured symbolic updates from primitives or skills."""
        if not updates:
            return
        for object_id, values in updates.get('objects', {}).items():
            self.objects.setdefault(object_id, {}).update(values)
        for location_id, values in updates.get('locations', {}).items():
            self.locations.setdefault(location_id, {}).update(values)
        if 'robot' in updates:
            self.robot.update(updates['robot'])

    def _entity(self, entity_id: str) -> dict[str, Any] | None:
        """Return an object or location dictionary by identifier."""
        return self.objects.get(entity_id) or self.locations.get(entity_id)

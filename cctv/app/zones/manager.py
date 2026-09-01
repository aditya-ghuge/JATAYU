import json
from typing import List, Tuple, Optional
from .zone import Zone


class ZoneManager:
    def __init__(self, config_path: str):
        self.zones: List[Zone] = []
        self._load_zones(config_path)

    def _load_zones(self, config_path: str):
        try:
            with open(config_path, "r") as f:
                zones_data = json.load(f)
                for zd in zones_data:
                    self.zones.append(Zone(**zd))
        except FileNotFoundError:
            print(f"Warning: Zone configuration file {config_path} not found.")
        except Exception as e:
            print(f"Error loading zones: {e}")

    def get_zone_for_point(self, point: Tuple[int, int]) -> Optional[str]:
        """
        Given a point (x, y), returns the zone_id of the zone it resides in, or None.
        """
        for zone in self.zones:
            if zone.contains(point):
                return zone.zone_id
        return None

    def get_all_zones(self) -> List[Zone]:
        return self.zones

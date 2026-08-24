from typing import List, Dict, Any
from tracking.models import TrackedPerson
from zones.manager import ZoneManager


class CrowdEngine:
    def __init__(self, zone_manager: ZoneManager):
        self.zone_manager = zone_manager

    def compute_metrics(self, tracked_people: List[TrackedPerson]) -> Dict[str, Any]:
        """
        Calculates occupancy metrics for all defined zones.
        """
        zones = self.zone_manager.get_all_zones()
        metrics = {"total_visible": len(tracked_people), "zones": []}

        # Count people per zone
        zone_counts = {zone.zone_id: 0 for zone in zones}

        for person in tracked_people:
            if person.current_zone and person.current_zone in zone_counts:
                zone_counts[person.current_zone] += 1

        # Generate metrics for each zone
        for zone in zones:
            count = zone_counts[zone.zone_id]
            occupancy_pct = (count / zone.capacity) * 100 if zone.capacity > 0 else 0

            # Determine crowd level
            if occupancy_pct <= 40:
                level = "LOW"
            elif occupancy_pct <= 70:
                level = "MODERATE"
            elif occupancy_pct <= 100:
                level = "HIGH"
            else:
                level = "CRITICAL"

            metrics["zones"].append(
                {
                    "zone_id": zone.zone_id,
                    "name": zone.name,
                    "people": count,
                    "capacity": zone.capacity,
                    "occupancy_percent": round(occupancy_pct, 1),
                    "crowd_level": level,
                }
            )

        return metrics

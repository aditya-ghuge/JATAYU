"""Central, event-driven building occupancy state.

Camera trackers identify people only within their own feed.  This engine keeps
the building count from entrance/exit boundary events and treats per-camera
zone sightings as location evidence, rather than pretending they are reliable
cross-camera identities.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Union

from .config import BuildingConfig
from .events import BoundaryCrossingEvent, ZoneTransitionEvent, utc_now

OccupancyEvent = Union[BoundaryCrossingEvent, ZoneTransitionEvent]


@dataclass
class PersonLocation:
    zone_id: str | None
    last_seen_at: str


class BuildingOccupancyEngine:
    def __init__(self, building_config: BuildingConfig, initial_occupancy: int = 0):
        if initial_occupancy < 0:
            raise ValueError("initial_occupancy cannot be negative")
        self.building_config = building_config
        self.initial_occupancy = initial_occupancy
        self.entries = 0
        self.exits = 0
        self.locations: dict[tuple[str, int], PersonLocation] = {}
        self._processed_event_ids: set[str] = set()
        self.emergency_started_at: str | None = None
        self.emergency_baseline: int | None = None
        self.confirmed_evacuated = 0
        self.unsafe_reentries = 0
        self._evacuated_source_tracks: set[tuple[str, int]] = set()
        self._post_baseline_entries: set[tuple[str, int]] = set()

    @property
    def current_occupancy(self) -> int:
        return max(0, self.initial_occupancy + self.entries - self.exits)

    def start_emergency(self, timestamp: str | None = None) -> dict:
        """Freeze the count used for evacuation accountability."""
        if self.emergency_baseline is None:
            self.emergency_started_at = timestamp or utc_now()
            self.emergency_baseline = self.current_occupancy
        return self.snapshot()

    def consume(self, event: OccupancyEvent) -> bool:
        """Apply one camera fact; returns False for a duplicate event."""
        if event.event_id in self._processed_event_ids:
            return False
        if not self.building_config.has_camera(event.camera_id):
            raise ValueError(f"Unknown camera_id: {event.camera_id}")

        self._processed_event_ids.add(event.event_id)
        source_track = (event.camera_id, event.track_id)

        if isinstance(event, ZoneTransitionEvent):
            self.locations[source_track] = PersonLocation(event.to_zone_id, event.timestamp)
            return True

        if event.direction == "INBOUND":
            self.entries += 1
            if self.emergency_baseline is not None:
                self.unsafe_reentries += 1
                if source_track in self._evacuated_source_tracks:
                    self._evacuated_source_tracks.remove(source_track)
                    self.confirmed_evacuated = max(0, self.confirmed_evacuated - 1)
                else:
                    # A person first observed entering after the baseline cannot be
                    # counted as one of the original occupants if they leave again.
                    self._post_baseline_entries.add(source_track)
        else:
            self.exits += 1
            self.locations.pop(source_track, None)
            if self.emergency_baseline is not None:
                if source_track in self._post_baseline_entries:
                    self._post_baseline_entries.remove(source_track)
                elif source_track not in self._evacuated_source_tracks:
                    self._evacuated_source_tracks.add(source_track)
                    self.confirmed_evacuated += 1
        return True

    def snapshot(self) -> dict:
        zone_counts = Counter(
            location.zone_id for location in self.locations.values() if location.zone_id
        )
        baseline = self.emergency_baseline
        potentially_remaining = (
            max(0, baseline - self.confirmed_evacuated) if baseline is not None else None
        )
        located = min(sum(zone_counts.values()), potentially_remaining or 0)
        return {
            "current_occupancy": self.current_occupancy,
            "confirmed_entries": self.entries,
            "confirmed_exits": self.exits,
            "emergency": {
                "active": baseline is not None,
                "started_at": self.emergency_started_at,
                "baseline": baseline,
                "confirmed_evacuated": self.confirmed_evacuated,
                "potentially_remaining": potentially_remaining,
                "located_in_zones": located,
                "unknown_unaccounted": (
                    max(0, potentially_remaining - located)
                    if potentially_remaining is not None
                    else None
                ),
                "unsafe_reentries": self.unsafe_reentries,
            },
            "zones": dict(sorted(zone_counts.items())),
        }

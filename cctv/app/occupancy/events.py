"""Small, serializable facts emitted by individual camera pipelines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ZoneTransitionEvent:
    camera_id: str
    track_id: int
    from_zone_id: str | None
    to_zone_id: str | None
    timestamp: str = ""
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", utc_now())
        if not self.event_id:
            object.__setattr__(self, "event_id", f"ZONE-{uuid.uuid4()}")

    def to_dict(self) -> dict:
        return {"type": "ZONE_TRANSITION", **asdict(self)}


@dataclass(frozen=True)
class BoundaryCrossingEvent:
    camera_id: str
    track_id: int
    boundary_id: str
    direction: Literal["INBOUND", "OUTBOUND"]
    timestamp: str = ""
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", utc_now())
        if not self.event_id:
            object.__setattr__(self, "event_id", f"BOUNDARY-{uuid.uuid4()}")

    def to_dict(self) -> dict:
        return {"type": "BOUNDARY_CROSSING", **asdict(self)}

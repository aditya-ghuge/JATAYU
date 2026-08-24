from pydantic import BaseModel, Field
from typing import List, Tuple


class TrackedPerson(BaseModel):
    track_id: int
    bbox: tuple[int, int, int, int]  # Current bounding box
    history: List[Tuple[int, int]] = Field(
        default_factory=list
    )  # List of past center points
    confidence: float
    time_since_update: int = 0  # Number of frames since last seen
    current_zone: str | None = None

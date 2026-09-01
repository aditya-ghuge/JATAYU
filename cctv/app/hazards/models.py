from pydantic import BaseModel


class HazardState(BaseModel):
    type: str  # "FIRE", "SMOKE", "DEBRIS"
    zone_id: str
    confidence: float
    status: str  # "DETECTING" or "CONFIRMED"
    frames_detected: int = 0
    frames_lost: int = 0

from pydantic import BaseModel


class Detection(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    track_id: int | None = None

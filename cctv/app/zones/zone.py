import cv2
import numpy as np
from pydantic import BaseModel
from typing import List, Tuple


class Zone(BaseModel):
    zone_id: str
    name: str
    capacity: int
    polygon: List[Tuple[int, int]]
    # Optional building metadata.  Existing camera-local zone files remain valid.
    zone_type: str = "room"
    floor: str | None = None

    @property
    def np_polygon(self):
        """Returns the polygon as a numpy array required by OpenCV."""
        return np.array(self.polygon, np.int32).reshape((-1, 1, 2))

    def contains(self, point: Tuple[int, int]) -> bool:
        """
        Check if the given (x, y) point is inside this zone's polygon.
        """
        # cv2.pointPolygonTest returns 1 if inside, 0 if on edge, -1 if outside
        result = cv2.pointPolygonTest(
            self.np_polygon, (point[0], point[1]), measureDist=False
        )
        return result >= 0

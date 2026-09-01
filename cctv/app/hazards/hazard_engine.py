from typing import List, Dict
from detection.models import Detection
from zones.manager import ZoneManager
from .models import HazardState


class HazardEngine:
    def __init__(
        self,
        zone_manager: ZoneManager,
        confirm_threshold: int = 15,
        lose_threshold: int = 10,
    ):
        """
        Args:
            confirm_threshold: Frames needed to confirm a hazard.
            lose_threshold: Frames without detection to drop the hazard.
        """
        self.zone_manager = zone_manager
        self.confirm_threshold = confirm_threshold
        self.lose_threshold = lose_threshold

        # Maps (type, zone_id) -> HazardState
        self.active_hazards: Dict[tuple, HazardState] = {}

    def update(self, detections: List[Detection]) -> List[HazardState]:
        """
        Process detections and apply temporal confirmation to hazards.
        """
        # Collect current frame hazards
        current_hazards = []
        for det in detections:
            if det.class_name in ["FIRE", "SMOKE", "DEBRIS"]:
                # Determine zone
                x1, y1, x2, y2 = det.bbox
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                zone_id = self.zone_manager.get_zone_for_point(center)
                if zone_id:
                    current_hazards.append(
                        {
                            "type": det.class_name,
                            "zone_id": zone_id,
                            "confidence": det.confidence,
                        }
                    )

        current_keys = set()
        for hz in current_hazards:
            key = (hz["type"], hz["zone_id"])
            current_keys.add(key)

            if key in self.active_hazards:
                state = self.active_hazards[key]
                state.frames_detected += 1
                state.frames_lost = 0
                state.confidence = hz["confidence"]
                if state.frames_detected >= self.confirm_threshold:
                    state.status = "CONFIRMED"
            else:
                self.active_hazards[key] = HazardState(
                    type=hz["type"],
                    zone_id=hz["zone_id"],
                    confidence=hz["confidence"],
                    status="DETECTING",
                    frames_detected=1,
                )

        # Handle lost hazards
        lost_keys = set(self.active_hazards.keys()) - current_keys
        for key in lost_keys:
            self.active_hazards[key].frames_lost += 1
            if self.active_hazards[key].frames_lost > self.lose_threshold:
                del self.active_hazards[key]

        return list(self.active_hazards.values())

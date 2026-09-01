import json
from typing import List, Tuple, Set, Dict, Any
from tracking.models import TrackedPerson


def lines_intersect(
    p1: Tuple[int, int], p2: Tuple[int, int], p3: Tuple[int, int], p4: Tuple[int, int]
) -> bool:
    """Check if line segment (p1, p2) intersects with line segment (p3, p4)."""

    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def get_direction(
    p1: Tuple[int, int], p2: Tuple[int, int], e1: Tuple[int, int], e2: Tuple[int, int]
) -> str:
    """
    Returns 'OUTBOUND' or 'INBOUND' depending on which way the movement vector crosses the exit vector.
    Uses the Z-component of the cross product.
    """
    # Vector of the exit line
    vx = e2[0] - e1[0]
    vy = e2[1] - e1[1]

    # Vector of the movement
    mx = p2[0] - p1[0]
    my = p2[1] - p1[1]

    # Cross product
    cross = (vx * my) - (vy * mx)
    return "OUTBOUND" if cross > 0 else "INBOUND"


class EvacuationEngine:
    def __init__(self, config_path: str):
        self.exits = []
        self._load_exits(config_path)

        # Keep track of which track IDs have already crossed an exit
        self.evacuated_ids: Set[int] = set()
        self.entered_ids: Set[int] = set()
        self.initial_population = 0

    def _load_exits(self, config_path: str):
        try:
            with open(config_path, "r") as f:
                self.exits = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Exit configuration file {config_path} not found.")
        except Exception as e:
            print(f"Error loading exits: {e}")

    def update(self, tracked_people: List[TrackedPerson]) -> Dict[str, Any]:
        """
        Check if any tracked person crossed an exit line.
        """
        # We need an initial population to calculate percentages (this would normally be dynamic)
        if self.initial_population == 0 and len(tracked_people) > 0:
            self.initial_population = 10  # Hardcoded for demo purposes

        alerts = []

        for person in tracked_people:
            # We need at least 2 points to form a movement line
            if (
                len(person.history) >= 2
                and person.track_id not in self.evacuated_ids
                and person.track_id not in self.entered_ids
            ):
                p1 = person.history[-2]
                p2 = person.history[-1]

                # Check against all exits
                for ex in self.exits:
                    exit_line = ex["line"]
                    e1 = tuple(exit_line[0])
                    e2 = tuple(exit_line[1])

                    if lines_intersect(p1, p2, e1, e2):
                        direction = get_direction(p1, p2, e1, e2)
                        if direction == "OUTBOUND":
                            print(
                                f"Person #{person.track_id} crossed {ex['name']} OUTBOUND!"
                            )
                            self.evacuated_ids.add(person.track_id)
                        else:
                            print(
                                f"ALERT! Person #{person.track_id} crossed {ex['name']} INBOUND!"
                            )
                            self.entered_ids.add(person.track_id)
                            alerts.append(f"Person #{person.track_id} ENTERED!")
                        break

        evacuated_count = len(self.evacuated_ids)
        entered_count = len(self.entered_ids)
        evac_percent = (
            (evacuated_count / self.initial_population) * 100
            if self.initial_population > 0
            else 0
        )

        return {
            "initial_population": self.initial_population,
            "evacuated": evacuated_count,
            "entered": entered_count,
            "evacuation_percentage": round(evac_percent, 1),
            "alerts": alerts,
        }

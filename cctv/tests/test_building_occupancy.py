import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from occupancy import (
    BoundaryCrossingEvent,
    BuildingConfig,
    BuildingOccupancyEngine,
    ZoneTransitionEvent,
)


class BuildingOccupancyEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = BuildingOccupancyEngine(
            BuildingConfig.from_json(Path(__file__).resolve().parents[1] / "config/cameras.json")
        )

    def test_entries_exits_and_duplicate_crossings(self):
        entry = BoundaryCrossingEvent("CAM-01", 1, "MAIN_DOOR", "INBOUND")
        self.assertTrue(self.engine.consume(entry))
        self.assertEqual(self.engine.current_occupancy, 1)
        self.assertFalse(self.engine.consume(entry))
        self.assertEqual(self.engine.current_occupancy, 1)

        self.engine.consume(BoundaryCrossingEvent("CAM-01", 2, "MAIN_DOOR", "INBOUND"))
        self.engine.consume(BoundaryCrossingEvent("CAM-01", 1, "MAIN_DOOR", "OUTBOUND"))
        self.assertEqual(self.engine.snapshot()["current_occupancy"], 1)

    def test_emergency_snapshot_separates_located_and_unknown_people(self):
        for track_id in (1, 2, 3):
            self.engine.consume(BoundaryCrossingEvent("CAM-01", track_id, "MAIN_DOOR", "INBOUND"))
        self.engine.consume(ZoneTransitionEvent("CAM-01", 1, None, "ROOM_A"))
        self.engine.start_emergency("2026-09-10T10:00:00+00:00")
        self.engine.consume(BoundaryCrossingEvent("CAM-01", 2, "MAIN_DOOR", "OUTBOUND"))

        emergency = self.engine.snapshot()["emergency"]
        self.assertEqual(emergency["baseline"], 3)
        self.assertEqual(emergency["confirmed_evacuated"], 1)
        self.assertEqual(emergency["potentially_remaining"], 2)
        self.assertEqual(emergency["located_in_zones"], 1)
        self.assertEqual(emergency["unknown_unaccounted"], 1)

    def test_reentry_is_recorded_during_emergency(self):
        self.engine.consume(BoundaryCrossingEvent("CAM-01", 5, "MAIN_DOOR", "INBOUND"))
        self.engine.start_emergency()
        self.engine.consume(BoundaryCrossingEvent("CAM-01", 6, "MAIN_DOOR", "INBOUND"))
        self.engine.consume(BoundaryCrossingEvent("CAM-01", 6, "MAIN_DOOR", "OUTBOUND"))
        state = self.engine.snapshot()
        self.assertEqual(state["emergency"]["unsafe_reentries"], 1)
        self.assertEqual(state["confirmed_exits"], 1)
        self.assertEqual(state["emergency"]["confirmed_evacuated"], 0)

    def test_rejects_unknown_cameras(self):
        with self.assertRaises(ValueError):
            self.engine.consume(BoundaryCrossingEvent("CAM-99", 1, "DOOR", "INBOUND"))


if __name__ == "__main__":
    unittest.main()

# PS14 CCTV AI Development Plan

## Phase 1 — Video Input

First make:

```
Camera
 ↓
OpenCV
 ↓
Frames
```

Support:

- Webcam
- Video file
- RTSP

**Done when:** The program can display a live video feed and report FPS.

---

## Phase 2 — Person Detection

Integrate YOLO.

Start with pretrained person detection.

**Output:**
- Person
- Bounding box
- Confidence

**Done when:** People are correctly detected in the video.

---

## Phase 3 — Tracking

Add tracking IDs.

Example:

```
Person #1
Person #2
Person #3
```

**Done when:** A person maintains a temporary ID across frames.

---

## Phase 4 — Zones

Create configurable polygons.

Example:

```
ZONE_A
ZONE_B
ZONE_C
EXIT_A
```

**Done when:** Every detected person can be assigned to the correct zone.

---

## Phase 5 — Crowd Intelligence

Calculate:

- Total people
- People per zone
- Capacity
- Occupancy %
- Crowd level
- Trend

**Done when:** The system can output:

```json
{
  "ZONE_A": 10,
  "ZONE_B": 7,
  "ZONE_C": 2
}
```

---

## Phase 6 — Exit Detection

Create virtual exit lines.

Track:

```
Inside
 ↓
Exit line
 ↓
Exited
```

Prevent duplicate counting.

**Done when:** One person crossing the exit is counted exactly once.

---

## Phase 7 — Evacuation

Implement:

- Initial population
- Exited
- Currently visible
- Remaining
- Potentially unaccounted
- Evacuation %

**Done when:** A controlled evacuation video produces correct statistics.

---

## Phase 8 — Fire / Smoke / Debris

Evaluate available models first.

If necessary, create a custom dataset.

Classes:

- FIRE
- SMOKE
- DEBRIS

Add temporal confirmation.

**Done when:** The system can demonstrate stable detection and generate hazard events.

---

## Phase 9 — Movement

Calculate:

- Direction
- Speed state
- Zone transition

**Done when:** The system can determine:

```
ZONE_A → ZONE_B
```

and approximate:

```
WALKING
RUNNING
STATIONARY
```

---

## Phase 10 — Unsafe Movement

Configure:

- Critical zones
- Active hazards
- Blocked exits
- Recommended exits

Detect:

- Person → critical zone
- Person → fire
- Person → smoke
- Person → blocked exit
- Person away from safe exit

Require persistence across multiple observations.

**Done when:** A controlled person moving toward a simulated fire produces `UNSAFE_MOVEMENT`.

---

## Phase 11 — JSON

Create two outputs.

- **State** — Current situation.
- **Event** — Something that happened.

Use `schema_version = 1.0`.

Validate with Pydantic.

---

## Phase 12 — API

Implement:

```
GET /health
GET /state
GET /events
```

The PS14 team should be able to retrieve your data without knowing anything about YOLO or OpenCV.

---

## Phase 13 — Testing

Create a mock mode.

Instead of AI:

- Mock person
- Mock fire
- Mock smoke
- Mock debris

This lets you test:

- Zones
- Counting
- Evacuation
- Events
- JSON
- API

without running the AI.

---

## Phase 14 — Final Demonstration

Your demo should show:

```
                 LIVE CCTV
                     │
                     ▼
          ┌────────────────────┐
          │ AI DETECTION       │
          │                    │
          │ 👤 👤 👤           │
          │       🔥           │
          │    🧱              │
          └────────────────────┘
                     │
                     ▼
              JSON OUTPUT
                     │
                     ▼
          PS14 CENTRAL SYSTEM
```

Demonstrate:

1. People entering.
2. People being counted.
3. People moving between zones.
4. Fire appearing.
5. Smoke appearing.
6. Critical zone being created.
7. Exit being detected.
8. People evacuating.
9. Exit count increasing.
10. Remaining population decreasing.
11. Person moving toward critical zone.
12. Unsafe movement alert.
13. JSON being sent to the main PS14 system.

---

## Priority

### P0 — Absolutely Required

- CCTV input
- OpenCV
- Person detection
- Tracking
- Zones
- Crowd count
- Exit counting
- JSON
- API

### P1 — Important

- Fire
- Smoke
- Debris
- Evacuation statistics
- Hazard events

### P2 — Advanced

- Unsafe movement
- Crowd surge
- Movement trends
- WebSocket
- Historical analytics
- Multi-camera support

Don't delay P0 because you're trying to perfect P2.

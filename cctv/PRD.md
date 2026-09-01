# PRD — PS14 CCTV AI Intelligence Module

## Product Name

PS14 CCTV Disaster Intelligence & Evacuation Monitoring System

## Purpose

Build an AI-powered CCTV analysis system that converts raw CCTV footage into structured, real-time disaster intelligence.

The system will:

```
CCTV → OpenCV → AI Vision → Tracking → Zone Analysis → Evacuation Analysis → JSON/API
```

The output will be consumed by the main PS14 disaster-management system.

---

## 2. Problem

During a disaster, CCTV cameras contain critical information, but raw video is difficult for an automated disaster-management system to interpret.

The system needs to automatically determine:

- How many people are present?
- Where are they?
- Which zones are crowded?
- Where is fire?
- Where is smoke?
- Where is debris?
- Which areas are critical?
- How many people have evacuated?
- How many people remain?
- Which exits are being used?
- Is someone moving toward a dangerous area?
- Is an exit blocked?
- Is the crowd increasing or decreasing?

The CCTV module converts these observations into structured data.

---

## 3. MVP Architecture

For the prototype:

**One physical camera**

The camera's field of view is divided into multiple logical zones.

```
                 CAMERA
                    │
                    ▼
        ┌─────────────────────┐
        │                     │
        │      ZONE A         │
        │                     │
        ├──────────┬──────────┤
        │ ZONE B   │ ZONE C 🔥│
        │          │          │
        ├──────────┴──────────┤
        │      EXIT A 🟢      │
        └─────────────────────┘
```

One camera therefore does not mean one zone.

The camera can monitor multiple zones as long as they are visible in its field of view.

---

## 4. Core Features

### F1 — CCTV Input

Support:

- Laptop webcam
- USB camera
- Local video
- IP camera
- RTSP stream

OpenCV handles video acquisition.

### F2 — Person Detection

AI detects people.

Each detection contains:

- Bounding Box
- Confidence
- Timestamp

### F3 — Person Tracking

Every detected person gets a temporary tracking ID.

Example:

```
Person #12
Person #13
Person #14
```

The system tracks movement between frames.

**Important:** Track IDs are not identities. No facial recognition is required.

---

## 5. Zone Detection

Zones are defined using polygons.

Example:

```json
{
  "zone_id": "ZONE_A",
  "name": "Corridor",
  "capacity": 15,
  "polygon": [
    [50,100],
    [300,100],
    [300,300],
    [50,300]
  ]
}
```

The system determines which zone a person occupies based on their bounding-box center.

---

## 6. Crowd Intelligence

For every zone:

- People Count
- Capacity
- Occupancy %
- Crowd Level
- Trend

Example:

```json
{
  "zone": "ZONE_A",
  "people": 14,
  "capacity": 15,
  "occupancy": 93,
  "crowd_level": "HIGH"
}
```

Suggested levels:

| Occupancy | Level |
|---|---|
| 0–40% | LOW |
| 40–70% | MODERATE |
| 70–100% | HIGH |
| >100% | CRITICAL |

These thresholds must remain configurable.

---

## 7. Fire Detection

AI detects: **FIRE**

Output:

```json
{
  "type": "FIRE",
  "zone": "ZONE_C",
  "confidence": 0.94
}
```

Fire should not trigger a critical event based on one uncertain frame.

Use temporal confirmation.

Example:

```
Frame 1 → 92%
Frame 2 → 94%
Frame 3 → 91%
Frame 4 → 95%
        ↓
CONFIRMED FIRE
```

---

## 8. Smoke Detection

Same concept: **SMOKE**

Output:

```json
{
  "type": "SMOKE",
  "zone": "ZONE_C",
  "confidence": 0.88
}
```

---

## 9. Debris Detection

Detect:

- DEBRIS
- OBSTRUCTION
- BLOCKED EXIT

Example:

```json
{
  "type": "DEBRIS",
  "zone": "EXIT_A",
  "confidence": 0.91
}
```

The system can then mark: `EXIT A = BLOCKED`

---

## 10. Evacuation Monitoring

This is one of the most important features.

The system must track:

- Initial population
- Currently visible
- Exited
- Remaining
- Potentially unaccounted
- Evacuation %

Example:

```json
{
  "initial_population": 30,
  "currently_visible": 12,
  "exited": 18,
  "potentially_unaccounted": 0,
  "evacuation_percentage": 60
}
```

### Exit detection

Create a virtual exit line:

```
          EXIT
           🚪
───────────┼──────────
           │
       EXIT LINE
```

When:

```
Person #17
INSIDE
 ↓
crosses line
 ↓
EXITED
```

increment the exit count.

The same track must never be counted twice.

---

## 11. Unsafe Evacuation Detection

The system should detect when people move toward dangerous areas.

Example:

```
              🔥
        CRITICAL ZONE
             ↑
             │
           👤
             │
             │
         ZONE A

        🟢 EXIT
```

If the person moves:

```
ZONE A → CRITICAL ZONE
```

generate: `UNSAFE_MOVEMENT`

Possible reasons:

- MOVING_TOWARD_FIRE
- MOVING_TOWARD_SMOKE
- MOVING_TOWARD_CRITICAL_ZONE
- MOVING_TOWARD_BLOCKED_EXIT
- MOVING_AWAY_FROM_SAFE_EXIT

Running can be recorded as an additional property.

Do not classify every running person as dangerous.

---

## 12. Movement Analysis

For every tracked person:

- Track ID
- Current zone
- Previous zone
- Direction
- Movement state

Movement states:

- STATIONARY
- WALKING
- RUNNING
- UNKNOWN

Example:

```json
{
  "track_id": 27,
  "previous_zone": "ZONE_A",
  "current_zone": "ZONE_C",
  "movement": "TOWARD_CRITICAL_ZONE",
  "speed_state": "RUNNING"
}
```

---

## 13. JSON Output

Your module should produce two types of information.

- **State** — "What is happening right now?"
- **Event** — "What just happened?"

### State JSON

```json
{
  "schema_version": "1.0",
  "timestamp": "2026-08-23T15:40:12+05:30",
  "camera": {
    "camera_id": "CAM_01",
    "status": "ONLINE"
  },
  "people": {
    "visible": 17,
    "tracked": 15
  },
  "zones": [
    {
      "id": "ZONE_A",
      "name": "Corridor",
      "people": 12,
      "capacity": 15,
      "occupancy_percent": 80,
      "crowd_level": "HIGH"
    }
  ],
  "hazards": [
    {
      "type": "FIRE",
      "zone": "ZONE_C",
      "confidence": 0.94,
      "status": "CONFIRMED"
    }
  ],
  "evacuation": {
    "initial_population": 30,
    "currently_visible": 12,
    "exited": 18,
    "potentially_unaccounted": 0,
    "evacuation_percentage": 60
  }
}
```

---

## 14. Event JSON

Example:

```json
{
  "event_id": "EVT_00127",
  "event_type": "UNSAFE_MOVEMENT",
  "timestamp": "2026-08-23T15:42:10+05:30",
  "camera_id": "CAM_01",
  "person": {
    "track_id": 27
  },
  "movement": {
    "from_zone": "ZONE_A",
    "to_zone": "ZONE_C",
    "direction": "TOWARD_CRITICAL_ZONE",
    "speed_state": "RUNNING"
  },
  "reason": "MOVING_TOWARD_FIRE",
  "confidence": 0.91,
  "severity": "HIGH"
}
```

---

## 15. Events

The system should support:

- FIRE_DETECTED
- SMOKE_DETECTED
- DEBRIS_DETECTED
- EXIT_CROSSED
- UNSAFE_MOVEMENT
- EXIT_BLOCKED
- CROWD_SURGE
- CAMERA_OFFLINE

---

## 16. Non-Goals

Your module should NOT:

- Decide the final evacuation route.
- Control emergency services.
- Perform facial recognition.
- Identify people by name.
- Claim that unseen people are missing.
- Detect things outside the camera's field of view.
- Require multiple cameras for the MVP.

The central PS14 system makes the final decisions.

---

## 17. Technology

### Required

- Python
- OpenCV
- YOLO
- NumPy
- FastAPI
- Pydantic
- JSON

### Optional

- SQLite/PostgreSQL
- WebSocket
- Docker

---

## 18. Hardware

### MVP

Laptop + 1 Camera

Your MacBook can handle development.

### Optional realistic setup

```
IP Camera
     ↓
Wi-Fi Router
     ↓
Laptop
```

No ESP32, Arduino, Raspberry Pi or sensors are required for your CCTV module.

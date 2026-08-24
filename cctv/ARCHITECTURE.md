# PS14 CCTV AI Architecture

## 1. High-Level Architecture

```
                    CCTV
                      │
                      ▼
              ┌───────────────┐
              │    OpenCV     │
              │ Video Capture │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ Preprocessing │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │   AI Engine   │
              │     YOLO      │
              └───────┬───────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       PERSON       FIRE/SMOKE   DEBRIS
          │           │           │
          ▼           ▼           ▼
       TRACKER     HAZARD      HAZARD
          │         ENGINE      ENGINE
          │
          ▼
    ┌──────────────┐
    │ Zone Engine  │
    └──────┬───────┘
           │
     ┌─────┼──────────────┐
     ▼     ▼              ▼
   CROWD  EXIT         MOVEMENT
  ENGINE  ENGINE         ENGINE
     │     │              │
     └─────┼──────────────┘
           ▼
    ┌──────────────┐
    │ Event Engine │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ JSON / API   │
    └──────┬───────┘
           │
           ▼
    PS14 CENTRAL SYSTEM
```

---

## 2. Project Structure

```
ps14-cctv/
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── video/
│   │   ├── webcam.py
│   │   ├── file.py
│   │   └── rtsp.py
│   │
│   ├── detection/
│   │   ├── detector.py
│   │   └── models.py
│   │
│   ├── tracking/
│   │   └── tracker.py
│   │
│   ├── zones/
│   │   ├── zone.py
│   │   └── manager.py
│   │
│   ├── hazards/
│   │   └── hazard_engine.py
│   │
│   ├── crowd/
│   │   └── crowd_engine.py
│   │
│   ├── evacuation/
│   │   └── evacuation_engine.py
│   │
│   ├── movement/
│   │   └── movement_engine.py
│   │
│   ├── events/
│   │   └── event_engine.py
│   │
│   ├── schemas/
│   │   └── output.py
│   │
│   └── api/
│       └── routes.py
│
├── config/
│   ├── zones.json
│   ├── exits.json
│   └── settings.json
│
├── models/
├── datasets/
├── tests/
├── requirements.txt
└── README.md
```

---

## 3. Module Responsibilities

### video

Only handles video input.

- Webcam
- Video File
- RTSP

### detection

Only handles AI inference.

**Input:** Frame

**Output:**
- Detection
- Bounding box
- Class
- Confidence

### tracking

Handles:

- Person IDs
- Positions
- Movement history

### zones

Handles:

- Polygon zones
- Zone assignment
- Zone transitions

### hazards

Handles:

- Fire
- Smoke
- Debris
- Temporal confirmation

### crowd

Handles:

- People count
- Zone occupancy
- Crowd level
- Crowd trends

### evacuation

Handles:

- Initial population
- Exit crossing
- Exited population
- Remaining population
- Evacuation percentage
- Potentially unaccounted estimate

### movement

Handles:

- Direction
- Speed state
- Zone transition
- Unsafe movement

### events

Converts observations into events.

### schemas

Ensures that every JSON response follows the agreed structure.

### api

Makes the information available to the rest of PS14.

Suggested:

```
GET /health
GET /state
GET /events
```

Later:

```
WebSocket /ws/live
```

# JATAYU CCTV — Building Occupancy & Evacuation Intelligence

The CCTV module is the visual-observation layer of JATAYU ResQRoute. It reads a camera feed, detects and tracks people, maps them to configured zones, reports crowd conditions, and produces building-occupancy events for emergency accountability.

It is designed to evolve incrementally: the existing YOLO + ByteTrack pipeline is preserved, while building-wide state is kept separately from any individual camera feed.

## What is implemented

| Area | Current capability |
| --- | --- |
| Video input | Webcam, video-file, and RTSP sources through OpenCV |
| Person detection | YOLO person detection |
| Tracking | ByteTrack IDs, bounding boxes, confidence, and short position history |
| Zones | Configurable polygon zones with capacity, floor, and zone type metadata |
| Crowd | Visible people per zone, occupancy percentage, and LOW/MODERATE/HIGH/CRITICAL crowd levels |
| Boundary monitoring | Virtual exit-line crossing with inbound/outbound direction |
| Building occupancy | Centralized entry/exit count and zone-transition events |
| Emergency accountability | Frozen baseline, confirmed evacuated, potentially remaining, located, unknown/unaccounted, and unsafe re-entry counts |
| API | Live state, recent events, MJPEG video stream, and emergency-baseline endpoint |

## Architecture

```text
Camera / Video source
        |
        v
OpenCV -> YOLO person detection -> ByteTrack
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
        Polygon zones        Crowd metrics        Exit-line crossings
              |                                         |
              +----------- Zone / boundary events ------+
                                                        |
                                                        v
                                      Building Occupancy Engine
                                                        |
                                  +---------------------+-------------------+
                                  |                     |                   |
                                  v                     v                   v
                           Live occupancy      Emergency snapshot       API / ResQRoute
```

### Camera-local versus building-wide truth

ByteTrack IDs are valid only within an individual camera feed. The module does **not** claim that `track_id=7` from one camera is the same person as `track_id=7` from another camera.

Instead:

- cameras emit facts: zone transitions and entrance/exit crossings;
- the central occupancy engine derives the building count from entry/exit facts;
- zone sightings provide the last known location for a camera-local track;
- unlocated people in an emergency remain explicitly `unknown_unaccounted`.

This avoids misleading cross-camera identity claims. Cross-camera person continuity is a later phase that needs a tested re-identification or controlled handoff design.

## Building occupancy and emergency flow

### Normal operation

1. A person crosses an entrance line inbound: `confirmed_entries` increases.
2. A person crosses an exit line outbound: `confirmed_exits` increases.
3. `current_occupancy` is derived from the configured starting count plus entries minus exits.
4. A person moving between polygon zones creates a `ZONE_TRANSITION` event.

### During an emergency

Call `POST /emergency/start` to freeze the current count as the emergency baseline. The returned state then reports:

| Field | Meaning |
| --- | --- |
| `baseline` | Occupancy at the moment the emergency was started |
| `confirmed_evacuated` | Baseline occupants confirmed crossing outbound after the snapshot |
| `potentially_remaining` | `baseline - confirmed_evacuated` |
| `located_in_zones` | Potentially remaining people with a known camera-local zone sighting |
| `unknown_unaccounted` | Potentially remaining people not currently located by available camera evidence |
| `unsafe_reentries` | Inbound crossings observed after the emergency began |

Known post-baseline entrants are not counted as evacuated when they later leave. This protects the emergency baseline from a simple, detectable re-entry case.

## Configuration

All operational geometry is data-driven so the same software can be used for a miniature demo or a different building.

### Cameras — `config/cameras.json`

Each active pipeline needs a unique `camera_id`.

```json
{
  "cameras": [
    {
      "camera_id": "CAM-01",
      "name": "Primary CCTV Feed",
      "role": "entrance_exit"
    }
  ]
}
```

### Zones — `config/zones.json`

Zones are polygons in that camera's pixel coordinates.

```json
{
  "zone_id": "ROOM_A",
  "name": "Room A",
  "capacity": 12,
  "zone_type": "room",
  "floor": "F1",
  "polygon": [[0, 0], [640, 0], [640, 480], [0, 480]]
}
```

`zone_type` and `floor` are optional; older zone files remain compatible. Typical zone types are `room`, `corridor`, `staircase`, and `exit`.

### Exit lines — `config/exits.json`

An exit line is a two-point virtual boundary. Its orientation determines which crossing direction is treated as `OUTBOUND` or `INBOUND`.

```json
{
  "exit_id": "EXIT_A",
  "name": "Main Door",
  "line": [[600, 300], [600, 700]]
}
```

Test the orientation with a controlled walkthrough before using it for a live demonstration.

## API

The API server runs on port `8001` when the module starts.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/state` | Latest camera, crowd, hazard, and building-occupancy state |
| `GET` | `/events` | Recent zone transitions, boundary crossings, and alerts |
| `GET` | `/video_feed` | MJPEG stream of the annotated video |
| `POST` | `/emergency/start` | Freeze the emergency occupancy baseline |

Example emergency start:

```bash
curl -X POST http://127.0.0.1:8001/emergency/start
```

The building state is returned under `population.building` in `/state`.

## Outputs available to other JATAYU components

Other modules should consume the API rather than reading detector or tracker internals. The CCTV module provides two kinds of output:

- **state** — the latest displayable view of the building;
- **events** — recent facts and alerts that happened at a particular time.

### Live state — `GET /state`

The response contains the fields below. This is the primary source for a dashboard, digital twin, or ResQRoute risk engine.

```json
{
  "timestamp": "2026-09-10T10:00:00+00:00",
  "camera_id": "CAM-01",
  "population": {
    "total_visible": 4,
    "evacuated": 1,
    "entered": 0,
    "zones": [
      {
        "zone_id": "ZONE_LEFT",
        "name": "Left Side",
        "people": 2,
        "capacity": 5,
        "occupancy_percent": 40.0,
        "crowd_level": "LOW"
      }
    ],
    "building": {
      "current_occupancy": 12,
      "confirmed_entries": 15,
      "confirmed_exits": 3,
      "emergency": {
        "active": true,
        "started_at": "2026-09-10T09:58:00+00:00",
        "baseline": 14,
        "confirmed_evacuated": 2,
        "potentially_remaining": 12,
        "located_in_zones": 4,
        "unknown_unaccounted": 8,
        "unsafe_reentries": 0
      },
      "zones": {
        "ZONE_LEFT": 2,
        "ZONE_RIGHT": 2
      }
    }
  },
  "hazards": [
    {
      "type": "FIRE",
      "zone": "ZONE_LEFT",
      "confidence": 0.91
    }
  ]
}
```

### What can be displayed now

| Display area | Fields to use |
| --- | --- |
| Camera status panel | `timestamp`, `camera_id`, `population.total_visible` |
| Zone cards / floor plan | `population.zones[*].people`, `capacity`, `occupancy_percent`, `crowd_level` |
| Building occupancy card | `population.building.current_occupancy`, `confirmed_entries`, `confirmed_exits` |
| Evacuation dashboard | `emergency.baseline`, `confirmed_evacuated`, `potentially_remaining` |
| People-accountability panel | `emergency.located_in_zones`, `unknown_unaccounted`, and `building.zones` |
| Re-entry warning | `emergency.unsafe_reentries` |
| Hazard overlay / route risk | `hazards[*].type`, `zone`, and `confidence` |
| CCTV view | `GET /video_feed` for the annotated MJPEG stream |

### Event stream — `GET /events`

Events are kept in arrival order in memory (up to the latest 100). The currently emitted event types are:

| Type | Meaning | Main fields |
| --- | --- | --- |
| `ZONE_TRANSITION` | A camera-local track changed zones | `camera_id`, `track_id`, `from_zone_id`, `to_zone_id`, `timestamp` |
| `BOUNDARY_CROSSING` | A track crossed an entrance/exit line | `camera_id`, `track_id`, `boundary_id`, `direction`, `timestamp` |
| `UNSAFE_ENTRY` | The legacy evacuation layer observed an inbound crossing | `priority`, `data.message`, `timestamp` |

Example zone-transition event:

```json
{
  "type": "ZONE_TRANSITION",
  "event_id": "ZONE-...",
  "timestamp": "2026-09-10T10:00:00+00:00",
  "camera_id": "CAM-01",
  "track_id": 12,
  "from_zone_id": "ROOM_A",
  "to_zone_id": "CORRIDOR_F1"
}
```

### Integration rules

- Use `population.building` for the **building-wide count**; do not add visible people across camera feeds.
- Use camera-local zone counts for visual context, not for cross-camera person identity.
- Treat `hazards` as provisional demo data until a dedicated fire/smoke model or sensor source is integrated.
- For emergency decisions, show `unknown_unaccounted` explicitly rather than assuming all potentially remaining people have been located.

## Local setup and running

From the `cctv` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app/main.py
```

Choose the video source in `app/config.py`. The application overlays zones, tracked people, exit lines, crowd metrics, and the existing evacuation display on the video window. Press `q` to stop it.

## Tests

Run the building-occupancy tests from the repository root:

```bash
PYTHONPATH=cctv/app python3 -m unittest discover -s cctv/tests -v
```

The current tests cover entry/exit counting, duplicate event handling, emergency baselines, re-entry treatment, located versus unknown people, and camera-configuration validation.

## Important limitations

### Fire and smoke detection

The current detector has placeholder mappings for fire/smoke-like classes from a general-purpose YOLO model. They are **not reliable fire or smoke detection** and must not be used as a safety-critical claim. The temporal hazard engine can be reused later with a dedicated, validated fire/smoke model or sensor input.

### Multi-camera operation

The building occupancy engine accepts camera-tagged events, but the executable currently starts one configured video pipeline (`CAM-01`). Running multiple feeds, camera-health monitoring, and cross-camera handoff are future implementation work.

### Occupancy confidence

Building occupancy depends on correctly placed entrance/exit lines and reliable detections. Missed crossings, occlusion, or an offline camera can make the count uncertain. The system exposes `unknown_unaccounted` rather than pretending every person has been located.

## Planned next increments

1. Start multiple configured camera pipelines and add camera-health events.
2. Add controlled room → corridor → staircase movement and camera handoff events without assuming identity continuity.
3. Integrate sensor-backed or dedicated-model hazard events.
4. Send structured occupancy, hazard, and route-blocking events to the ResQRoute risk and routing engine.

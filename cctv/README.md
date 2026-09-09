# PS14 CCTV Disaster Intelligence Module

This module processes CCTV video feeds to generate structured JSON data (state and events) using AI, as part of the PS14 system.

## Phase 1: Video Input

Currently implements basic video capture capabilities (webcam, file, RTSP) with FPS calculation.

## Building occupancy (first incremental phase)

The existing YOLO + ByteTrack pipeline remains camera-local.  The new
`app/occupancy` layer consumes two kinds of camera facts:

- `ZONE_TRANSITION`: a track moved between configured zones in one camera.
- `BOUNDARY_CROSSING`: a track crossed an entrance/exit line inbound or outbound.

It keeps the building count from entrance/exit events and exposes it within
`GET /state` at `population.building`.  Start an emergency snapshot with:

```bash
curl -X POST http://127.0.0.1:8001/emergency/start
```

The snapshot includes `confirmed_evacuated`, `potentially_remaining`, and
`unknown_unaccounted`.  Camera-local sightings are intentionally only location
evidence: ByteTrack IDs cannot safely be treated as cross-camera identities.
Cross-camera identity continuity is a later phase and must be introduced only
with a suitable re-identification strategy or a controlled hand-off design.

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running

```bash
python3 app/main.py
```

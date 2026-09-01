# PS14 CCTV Disaster Intelligence Module

This module processes CCTV video feeds to generate structured JSON data (state and events) using AI, as part of the PS14 system.

## Phase 1: Video Input

Currently implements basic video capture capabilities (webcam, file, RTSP) with FPS calculation.

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

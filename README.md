# JATAYU Repository

This repository contains the backend implementation of the JATAYU Smart India Hackathon project.
It includes the CCTV module, routing engine, backend APIs, and supporting services used for emergency evacuation.

# Repository Contents

- `cctv/` – YOLO-based person detection, tracking and zone mapping.
- `routealgo/` – Dynamic evacuation route generation.
- `services/` – Supporting backend services.
- `app.py` – Main backend entry point.
- `database.py` – Database configuration.
- `models.py` – Data models.
- `schemas.py` – API schemas.

# Features Available

- CCTV person detection
- Crowd counting
- Zone mapping (C1/C2)
- FastAPI backend APIs
- Dynamic route generation
- Live risk monitoring

# Tech Stack

Python • FastAPI • OpenCV • YOLOv8 • NetworkX • SQLite • SQLAlchemy • Pydantic

# Running the Project

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Start the application:

   ```bash
   python app.py
   ```
Dashboard
<img width="1894" height="884" alt="Screenshot 2026-09-16 224110" src="https://github.com/user-attachments/assets/64abb94e-8bcf-45ef-a263-826b59ed4c45" />
JATAYU Live Dashboard – Real-time building status, risk monitoring, and evacuation route visualization.

CCTV Monitoring
<img width="1891" height="870" alt="Screenshot 2026-09-16 223726" src="https://github.com/user-attachments/assets/d9a18d2a-4f33-4d6d-b5e8-85bacc281c86" />
CCTV Module – YOLOv8-based person detection, tracking, and crowd monitoring.



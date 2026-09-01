"""
ResQRoute AI - CCTV / OpenCV Crowd Ingestion Client
===================================================
Demonstrates how computer vision / OpenCV camera feeds estimate crowd counts
and send updates to the ResQRoute AI FastAPI backend.
"""

import time
import requests

API_URL = "http://localhost:8000/crowd"


def report_crowd(zone_id: str, crowd_count: float):
    """Sends crowd count to FastAPI backend."""
    payload = {
        "zone_id": zone_id,
        "crowd_count": float(crowd_count)
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=2.0)
        if resp.status_code == 200:
            print(f"[CCTV Feed] Zone {zone_id} crowd updated: {crowd_count:.0f} people. Response: {resp.json()}")
        else:
            print(f"[CCTV Feed] Error updating {zone_id}: {resp.status_code}")
    except Exception as e:
        print(f"[CCTV Feed] Connection failed: {e}")


def simulate_cctv_crowd_stream():
    """Simulates periodic CCTV pedestrian counting in corridors."""
    print("--- Starting CCTV Crowd Feed Simulation ---")
    corridor_data = [
        ("C1", 15.0),
        ("C2", 85.0),  # Heavy bottleneck in C2
        ("C3", 5.0),
        ("C4", 2.0),
    ]

    for zone, count in corridor_data:
        report_crowd(zone, count)
        time.sleep(0.5)


if __name__ == "__main__":
    simulate_cctv_crowd_stream()

# pyrefly: ignore [missing-import]
import cv2
import sys
import requests
from config import settings
from video import get_video_source
from detection import YOLODetector
from tracking import PersonTracker
from zones import ZoneManager
from crowd import CrowdEngine
from evacuation import EvacuationEngine
from hazards import HazardEngine
from api import store, run_server
import threading
import datetime
import uuid


def main():
    print("Starting CCTV")
    print(f"Source Type: {settings.VIDEO_SOURCE_TYPE}")
    print(f"Source Path: {settings.VIDEO_SOURCE_PATH}")

    detector = YOLODetector(conf_threshold=0.5)

    print("Initializing Tracker...")
    tracker = PersonTracker(history_length=30, max_age=30)

    print("Loading Zones and Exits...")
    zone_manager = ZoneManager("config/zones.json")
    crowd_engine = CrowdEngine(zone_manager)
    evac_engine = EvacuationEngine("config/exits.json")
    hazard_engine = HazardEngine(zone_manager, confirm_threshold=15, lose_threshold=10)

    print("Starting API Server...")
    api_thread = threading.Thread(
        target=run_server, kwargs={"host": "0.0.0.0", "port": 8001}, daemon=True
    )
    api_thread.start()

    try:
        source = get_video_source(
            settings.VIDEO_SOURCE_TYPE, settings.VIDEO_SOURCE_PATH
        )
        source.start()
    except Exception as e:
        print(f"Error initializing video source: {e}")
        sys.exit(1)

    print("Video source started successfully. Press 'q' to exit.")

    import time

    alert_active_until = 0
    last_alert_msg = ""

    try:
        while True:
            ret, frame = source.read()
            if not ret:
                print("End of video stream or failed to read frame.")
                break

            fps = source.get_fps()

            # Detect objects
            detections = detector.predict(frame)

            # Separate detections
            person_detections = [d for d in detections if d.class_name == "person"]

            # Update Engines
            tracked_people = tracker.update(person_detections)
            hazard_states = hazard_engine.update(detections)

            # Compute Crowd Metrics & Evacuation
            crowd_metrics = crowd_engine.compute_metrics(tracked_people)
            evac_metrics = evac_engine.update(tracked_people)

            # Format and Push State
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

            state_json = {
                "timestamp": timestamp,
                "camera_id": "CAM-01",
                "population": {
                    "total_visible": crowd_metrics.get("total_visible", 0),
                    "evacuated": evac_metrics.get("evacuated", 0),
                    "entered": evac_metrics.get("entered", 0),
                    "zones": crowd_metrics.get("zones", []),
                },
                "hazards": [],
            }

            for hz in hazard_states:
                if hz.status == "CONFIRMED":
                    state_json["hazards"].append(
                        {
                            "type": hz.type,
                            "zone": hz.zone_id,
                            "confidence": hz.confidence,
                        }
                    )

                        store.update_state(state_json)

            # Send crowd data to RouteAlgo
            zone_map = {
                "ZONE_LEFT": "C1",
                "ZONE_RIGHT": "C3"
            }

            for zone in crowd_metrics.get("zones", []):
                try:
                    requests.post(
                        "http://127.0.0.1:8000/crowd",
                        json={
                            "zone_id": zone_map.get(zone["name"], "C1"),
                            "crowd_count": zone["people"]
                        },
                        timeout=1
                    )
                except Exception:
                    pass

            # Generate Entry Events
            for alert in evac_metrics.get("alerts", []):
                event_json = {
                    "event_id": f"EVT-{str(uuid.uuid4())[:8]}",
                    "timestamp": timestamp,
                    "type": "UNSAFE_ENTRY",
                    "priority": "CRITICAL",
                    "data": {"message": alert},
                }
                store.add_event(event_json)

            # Generate Entry Events
            for alert in evac_metrics.get("alerts", []):
                event_json = {
                    "event_id": f"EVT-{str(uuid.uuid4())[:8]}",
                    "timestamp": timestamp,
                    "type": "UNSAFE_ENTRY",
                    "priority": "CRITICAL",
                    "data": {"message": alert},
                }
                store.add_event(event_json)

            # Draw Zones and Exits
            overlay = frame.copy()
            for zone in zone_manager.get_all_zones():
                cv2.polylines(
                    overlay,
                    [zone.np_polygon],
                    isClosed=True,
                    color=(255, 0, 0),
                    thickness=2,
                )
                cv2.fillPoly(overlay, [zone.np_polygon], color=(255, 0, 0))
            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

            for ex in evac_engine.exits:
                pt1, pt2 = ex["line"][0], ex["line"][1]
                cv2.line(frame, tuple(pt1), tuple(pt2), (0, 0, 255), 4)
                cv2.putText(
                    frame,
                    ex["name"],
                    tuple(pt1),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2,
                )

            # Draw tracked people and calculate zones
            for person in tracked_people:
                x1, y1, x2, y2 = person.bbox
                track_id = person.track_id

                # Assign Zone based on latest center point
                latest_center = person.history[-1]
                person.current_zone = zone_manager.get_zone_for_point(latest_center)
                zone_label = person.current_zone if person.current_zone else "NO_ZONE"

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Draw label
                label = f"Person #{track_id} ({zone_label})"
                cv2.putText(
                    frame,
                    label,
                    (x1, max(y1 - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

                # Draw history trail
                if len(person.history) > 1:
                    for i in range(1, len(person.history)):
                        pt1 = person.history[i - 1]
                        pt2 = person.history[i]
                        cv2.line(frame, pt1, pt2, (0, 255, 255), 2)

            # Draw Hazards
            for hz in hazard_states:
                # Find the zone to draw the warning
                if hz.status == "CONFIRMED":
                    # Flashing red background for critical hazards
                    if int(time.time() * 4) % 2 == 0:
                        cv2.rectangle(
                            frame,
                            (0, 0),
                            (frame.shape[1], frame.shape[0]),
                            (0, 0, 255),
                            10,
                        )

                    alert_text = f"CRITICAL: {hz.type} IN {hz.zone_id}!"
                    (w, h), _ = cv2.getTextSize(
                        alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3
                    )
                    cv2.putText(
                        frame,
                        alert_text,
                        ((frame.shape[1] - w) // 2, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.5,
                        (0, 0, 255),
                        3,
                    )
                elif hz.status == "DETECTING":
                    # Draw subtle detecting text
                    cv2.putText(
                        frame,
                        f"Detecting {hz.type}...",
                        (10, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 165, 255),
                        2,
                    )

            # Draw FPS
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            # Compress and push frame to API Store
            ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                store.update_frame(buffer.tobytes())

            # Draw Evacuation Metrics
            evac_text = f"Evacuated: {evac_metrics['evacuated']}/{evac_metrics['initial_population']} ({evac_metrics['evacuation_percentage']}%)"
            entered_text = f"Entered (HAZARD): {evac_metrics['entered']}"
            cv2.putText(
                frame,
                evac_text,
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                entered_text,
                (10, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

            # Handle Entry Alerts
            if evac_metrics["alerts"]:
                alert_active_until = time.time() + 3  # Keep alert active for 3 seconds
                last_alert_msg = evac_metrics["alerts"][-1]

            if time.time() < alert_active_until:
                if int(time.time() * 4) % 2 == 0:  # Fast flashing effect
                    text = f"ALERT: {last_alert_msg}"
                    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
                    cv2.putText(
                        frame,
                        text,
                        ((frame.shape[1] - w) // 2, frame.shape[0] // 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.5,
                        (0, 0, 255),
                        3,
                    )

            # Draw Crowd Metrics
            y_offset = 115
            for z_metric in crowd_metrics["zones"]:
                z_text = f"{z_metric['name']}: {z_metric['people']} ({z_metric['crowd_level']})"
                cv2.putText(
                    frame,
                    z_text,
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                y_offset += 30

            # Display frame
            cv2.imshow("CCTV", frame)

            # Exit on 'q' press
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        print("Cleaning up...")
        source.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

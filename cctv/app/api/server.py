import uvicorn
import time
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from .store import store

app = FastAPI(title="CCTV API")


@app.get("/state")
def get_state():
    return store.get_state()


@app.get("/events")
def get_events():
    return {"events": store.get_events()}


@app.post("/emergency/start")
def start_emergency():
    """Freeze the live occupancy as the evacuation accountability baseline."""
    try:
        return {"building": store.start_emergency()}
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def generate_frames():
    while True:
        frame = store.get_frame()
        if frame is not None:
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.05)  # ~20 FPS limit to prevent CPU overload


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


def run_server(host="0.0.0.0", port=8000):
    """
    Run the uvicorn server. Designed to be called from a background thread.
    """
    uvicorn.run(app, host=host, port=port, log_level="error")

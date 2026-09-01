from .webcam import WebcamSource
from .file import FileVideoSource
from .rtsp import RTSPVideoSource


def get_video_source(source_type: str, path: str):
    source_type = source_type.lower()
    if source_type == "webcam":
        return WebcamSource(path)
    elif source_type == "file":
        return FileVideoSource(path)
    elif source_type == "rtsp":
        return RTSPVideoSource(path)
    else:
        raise ValueError(f"Unknown video source type: {source_type}")

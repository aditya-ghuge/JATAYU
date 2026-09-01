from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    VIDEO_SOURCE_TYPE: str = "webcam"  # Options: webcam, file, rtsp
    VIDEO_SOURCE_PATH: Optional[str] = (
        "0"  # "0" for webcam, file path for file, URL for rtsp
    )

    class Config:
        env_file = ".env"


settings = Settings()

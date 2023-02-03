from typing import List, Optional

from pydantic import BaseSettings, HttpUrl
from pydantic.networks import AnyHttpUrl


class Settings(BaseSettings):
    class Config:
        env_file = ".env"

    PROJECT_NAME: str = "defi-platform-api"

    SENTRY_DSN: Optional[HttpUrl] = None

    API_PATH: str = "/api/v1"

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []


settings = Settings()

from pydantic import BaseSettings, HttpUrl
from pydantic.networks import AnyHttpUrl


class Settings(BaseSettings):
    class Config:
        env_file = ".env"

    PROJECT_NAME: str = "defi-platform-api"

    SENTRY_DSN: HttpUrl | None = None

    API_PATH: str = "/api/v1"

    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []


settings = Settings()

# -*- coding: utf-8 -*-

import functools

import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """Runtime configuration derived from the environment."""

    app_name: str = "PowerPlant API"
    app_version: str = "0.1.0"
    app_port: int = 8888
    log_level: str = "INFO"

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="POWERPLANT_", env_file=".env", extra="ignore")


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()

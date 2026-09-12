"""
Centralized configuration, loaded from environment variables (12-factor style).
Never hard-code secrets here — everything comes from the environment / .env file.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    github_token: str
    github_owner: str
    github_repo: str
    webhook_secret: str
    port: int = 8000

    github_api_base: str = "https://api.github.com"
    request_timeout_seconds: float = 10.0

    @property
    def repo_path(self) -> str:
        return f"{self.github_owner}/{self.github_repo}"


@lru_cache
def get_settings() -> Settings:
    # lru_cache means env is read once per process; tests override via
    # dependency_overrides or by monkeypatching env vars + clearing the cache.
    return Settings()

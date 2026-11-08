"""Settings read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

# Repo checkout and image both keep schemas/ next to src/.
DEFAULT_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise KeyError(f"{name} is not set")
    return value


@dataclass(frozen=True)
class S3Settings:
    endpoint: str
    bucket: str
    region: str
    access_key: str
    secret_key: str

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            endpoint=_env("S3_ENDPOINT"),
            bucket=_env("S3_BUCKET", "wifi-raw"),
            region=_env("S3_REGION", "garage"),
            access_key=_env("S3_ACCESS_KEY"),
            secret_key=_env("S3_SECRET_KEY"),
        )


@dataclass(frozen=True)
class Settings:
    max_body_bytes: int = 2 * 1024 * 1024
    rate_limit: int = 30
    rate_window_s: int = 3600
    schema_dir: Path = DEFAULT_SCHEMA_DIR

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            max_body_bytes=int(_env("MAX_BODY_BYTES", str(cls.max_body_bytes))),
            rate_limit=int(_env("RATE_LIMIT", str(cls.rate_limit))),
            rate_window_s=int(_env("RATE_WINDOW_S", str(cls.rate_window_s))),
            schema_dir=Path(_env("SCHEMA_DIR", str(DEFAULT_SCHEMA_DIR))),
        )


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    trusted_proxies: str

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            host=_env("HOST", "0.0.0.0"),
            port=int(_env("PORT", "8000")),
            trusted_proxies=_env("TRUSTED_PROXIES", "127.0.0.1"),
        )

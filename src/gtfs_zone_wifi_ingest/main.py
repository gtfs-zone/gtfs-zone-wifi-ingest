"""Console entry point: runs the API under uvicorn."""

from __future__ import annotations

import logging

import uvicorn

from gtfs_zone_wifi_ingest.app import create_app
from gtfs_zone_wifi_ingest.config import S3Settings, ServerSettings, Settings
from gtfs_zone_wifi_ingest.store import SessionStore, s3_store


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    server = ServerSettings.from_env()
    app = create_app(Settings.from_env(), SessionStore(s3_store(S3Settings.from_env())))
    uvicorn.run(
        app,
        host=server.host,
        port=server.port,
        proxy_headers=True,
        forwarded_allow_ips=server.trusted_proxies,
        # The app logs requests itself, without the client address.
        access_log=False,
        log_config=None,
    )

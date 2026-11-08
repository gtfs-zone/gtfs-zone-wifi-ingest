import json
import socket
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import pytest
from fastapi.testclient import TestClient
from moto.server import ThreadedMotoServer

from gtfs_zone_wifi_ingest.app import create_app
from gtfs_zone_wifi_ingest.config import S3Settings, Settings
from gtfs_zone_wifi_ingest.store import SessionStore, s3_store

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sessions"
KEY = "testing"


class Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


@pytest.fixture(scope="session")
def moto_endpoint():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=port)
    server.start()
    yield f"http://127.0.0.1:{port}"
    server.stop()


@pytest.fixture
def s3(moto_endpoint):
    """A fresh bucket on the moto server, and a boto3 client to inspect it."""
    bucket = f"wifi-raw-{uuid.uuid4().hex[:12]}"
    client = boto3.client(
        "s3",
        endpoint_url=moto_endpoint,
        region_name="us-east-1",
        aws_access_key_id=KEY,
        aws_secret_access_key=KEY,
    )
    client.create_bucket(Bucket=bucket)
    settings = S3Settings(
        endpoint=moto_endpoint,
        bucket=bucket,
        region="us-east-1",
        access_key=KEY,
        secret_key=KEY,
    )
    return settings, client


def keys(s3) -> list[str]:
    settings, client = s3
    resp = client.list_objects_v2(Bucket=settings.bucket)
    return sorted(o["Key"] for o in resp.get("Contents", []))


@pytest.fixture
def clock():
    return Clock(datetime(2026, 11, 8, 15, 0, tzinfo=UTC))


@pytest.fixture
def store(s3, clock):
    return SessionStore(s3_store(s3[0]), clock=clock)


@pytest.fixture
def make_client(store):
    def make(**overrides):
        return TestClient(create_app(Settings(**overrides), store))

    return make


@pytest.fixture
def client(make_client):
    return make_client()


def fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())

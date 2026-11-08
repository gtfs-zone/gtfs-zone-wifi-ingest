import copy
import gzip
import json
import logging
from datetime import datetime

import pytest
from conftest import FIXTURE_DIR, fixture, keys

FIXTURES = sorted(FIXTURE_DIR.glob("*.json"))
JSON = {"Content-Type": "application/json"}


def post(client, body: bytes, headers=None):
    return client.post(
        "/v1/sessions", content=body, headers={**JSON, **(headers or {})}
    )


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_generate_204(client):
    resp = client.get("/generate_204")
    assert resp.status_code == 204
    assert resp.content == b""
    assert resp.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_is_created(client, s3, path):
    body = path.read_bytes()
    session_id = json.loads(body)["session_id"]
    resp = post(client, body)
    assert resp.status_code == 201
    assert resp.json() == {"session_id": session_id, "status": "created"}
    raw = f"raw/v1/2026/11/08/{session_id}.json"
    assert keys(s3) == [f"ids/{session_id}", raw]
    settings, boto = s3
    obj = boto.get_object(Bucket=settings.bucket, Key=raw)
    assert obj["Body"].read() == body
    assert obj["ContentType"] == "application/json"


def test_gzip_upload(client, s3):
    body = (FIXTURE_DIR / "trip-good-wifi.json").read_bytes()
    resp = post(client, gzip.compress(body), {"Content-Encoding": "gzip"})
    assert resp.status_code == 201
    settings, boto = s3
    session_id = json.loads(body)["session_id"]
    obj = boto.get_object(
        Bucket=settings.bucket, Key=f"raw/v1/2026/11/08/{session_id}.json"
    )
    assert obj["Body"].read() == body


def test_duplicate_returns_200(client, s3):
    body = (FIXTURE_DIR / "trip-good-wifi.json").read_bytes()
    assert post(client, body).status_code == 201
    before = keys(s3)
    resp = post(client, body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "exists"
    assert keys(s3) == before


def test_duplicate_on_a_later_day(client, s3, clock):
    body = (FIXTURE_DIR / "trip-good-wifi.json").read_bytes()
    assert post(client, body).status_code == 201
    before = keys(s3)
    clock.at = datetime(2026, 11, 9, 9, 0, tzinfo=clock.at.tzinfo)
    assert post(client, body).status_code == 200
    assert keys(s3) == before


def test_missing_raw_object_is_repaired(client, s3):
    body = (FIXTURE_DIR / "trip-good-wifi.json").read_bytes()
    session_id = json.loads(body)["session_id"]
    raw = f"raw/v1/2026/11/08/{session_id}.json"
    assert post(client, body).status_code == 201
    settings, boto = s3
    boto.delete_object(Bucket=settings.bucket, Key=raw)
    assert post(client, body).status_code == 200
    assert raw in keys(s3)


def test_invalid_json(client, s3):
    resp = post(client, b"{not json")
    assert resp.status_code == 400
    assert keys(s3) == []


def test_invalid_gzip(client):
    resp = post(client, b"not gzip at all", {"Content-Encoding": "gzip"})
    assert resp.status_code == 400


def test_unsupported_encoding(client):
    resp = post(client, b"{}", {"Content-Encoding": "br"})
    assert resp.status_code == 415


def test_schema_violation(client, s3):
    session = copy.deepcopy(fixture("trip-good-wifi.json"))
    session["device_id"] = "abc"
    resp = post(client, json.dumps(session).encode())
    assert resp.status_code == 422
    assert resp.json()["errors"]
    assert keys(s3) == []


def test_unknown_schema_version(client):
    session = fixture("trip-good-wifi.json")
    session["schema_version"] = 99
    resp = post(client, json.dumps(session).encode())
    assert resp.status_code == 422
    assert resp.json()["errors"] == ["$.schema_version: must be one of 1"]


def test_not_an_object(client):
    resp = post(client, b"[]")
    assert resp.status_code == 422


def test_oversize_body(make_client, s3):
    client = make_client(max_body_bytes=1000)
    body = (FIXTURE_DIR / "trip-good-wifi.json").read_bytes()
    assert len(body) > 1000
    assert post(client, body).status_code == 413
    assert keys(s3) == []


def test_default_limit_is_2_mb(client):
    assert post(client, b" " * (2 * 1024 * 1024 + 1)).status_code == 413


def test_oversize_after_gunzip(make_client, s3):
    client = make_client(max_body_bytes=10_000)
    bomb = gzip.compress(b" " * 1_000_000)
    assert len(bomb) < 10_000
    resp = post(client, bomb, {"Content-Encoding": "gzip"})
    assert resp.status_code == 413
    assert keys(s3) == []


def test_rate_limited(client):
    body = (FIXTURE_DIR / "trip-good-wifi.json").read_bytes()
    statuses = [post(client, body).status_code for _ in range(31)]
    assert statuses[0] == 201
    assert set(statuses[1:30]) == {200}
    assert statuses[30] == 429
    resp = post(client, body)
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) > 0


def test_rate_limit_counts_rejected_uploads(make_client):
    client = make_client(rate_limit=2)
    assert post(client, b"x").status_code == 400
    assert post(client, b"x").status_code == 400
    assert post(client, b"x").status_code == 429


def test_logs_never_contain_the_client_address(client, caplog):
    caplog.set_level(logging.DEBUG)
    body = (FIXTURE_DIR / "trip-good-wifi.json").read_bytes()
    post(client, body, {"X-Forwarded-For": "203.0.113.7"})
    post(client, b"{bad")
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "session=" in text
    assert "testclient" not in text
    assert "203.0.113.7" not in text

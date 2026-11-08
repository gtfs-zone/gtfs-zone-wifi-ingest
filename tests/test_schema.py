import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parent.parent
SCHEMA = json.loads((ROOT / "schemas" / "session.v1.json").read_text())
FIXTURES = sorted((ROOT / "tests" / "fixtures" / "sessions").glob("*.json"))
VALIDATOR = Draft202012Validator(
    SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER
)


def load(name: str) -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "sessions" / name).read_text())


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_three_fixtures():
    assert len(FIXTURES) == 3


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_is_valid(path):
    VALIDATOR.validate(json.loads(path.read_text()))


def _extra_key(s):
    s["device_id"] = "abc"


def _extra_sample_key(s):
    s["samples"][0]["imei"] = "123"


def _bad_enum(s):
    s["reports"]["portal"] = "captcha"


def _missing_trip(s):
    del s["trip"]


def _station_on_trip(s):
    s["station_checklist"] = {"needed_email": True}


def _bad_uuid(s):
    s["session_id"] = "not-a-uuid"


def _local_time(s):
    s["started_at"] = "2026-11-08T14:19:00+01:00"


def _bad_bssid(s):
    s["samples"][0]["wifi"]["bssid"] = "02-1A-2B-3C-4D-5E"


def _bad_version(s):
    s["schema_version"] = 2


def _extra_stop_key(s):
    s["trip"]["boarding"]["platform"] = "1"


@pytest.mark.parametrize(
    "mutate",
    [
        _extra_key,
        _extra_sample_key,
        _bad_enum,
        _missing_trip,
        _station_on_trip,
        _bad_uuid,
        _local_time,
        _bad_bssid,
        _bad_version,
        _extra_stop_key,
    ],
    ids=lambda f: f.__name__.strip("_"),
)
def test_trip_mutation_is_rejected(mutate):
    session = copy.deepcopy(load("trip-good-wifi.json"))
    mutate(session)
    assert not VALIDATOR.is_valid(session)


def _reports_on_station(s):
    s["reports"] = {"wifi": "works"}


def _missing_checklist(s):
    del s["station_checklist"]


def _scheduled_time_on_station(s):
    s["station"]["scheduled_time"] = "2026-11-08T17:30:00Z"


@pytest.mark.parametrize(
    "mutate",
    [_reports_on_station, _missing_checklist, _scheduled_time_on_station],
    ids=lambda f: f.__name__.strip("_"),
)
def test_station_mutation_is_rejected(mutate):
    session = copy.deepcopy(load("station-checklist.json"))
    mutate(session)
    assert not VALIDATOR.is_valid(session)

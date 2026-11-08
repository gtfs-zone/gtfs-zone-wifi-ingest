# Session schema

`session.v1.json` (JSON Schema 2020-12) is the upload format for
gtfs-zone-wifi-app. gtfs-zone-wifi-pipeline and the app pin a copy and test
against it. Example sessions are in `tests/fixtures/sessions/`.

## Versioning

- `schema_version` is an integer and the file name carries it
  (`session.v<N>.json`).
- Adding an optional field keeps the version. Anything that makes an old
  session invalid, or changes a field's meaning, is a new version.
- Ingest accepts every version it has a schema for. Raw sessions are kept in
  the version they were uploaded in.

## Conventions

- Timestamps are RFC 3339 in UTC (`Z`).
- Units: metres, m/s, dBm, MHz, ms, bytes.
- `null` means unknown or not answered. A field that is not in the schema is
  rejected.
- Nothing links one session to another: no device id, no account, no IP.

## Trip and stop ids

Sessions store the Transitous ids as returned, and the GTFS ids derived from
them in `trip.gtfs` and `gtfs_stop_id` (null when they cannot be derived), so
a session survives a change in the Transitous id format.

What Transitous `/api/v6/stoptimes` and `/api/v6/trip` return (checked
2026-11-08):

| Field | Format | Example |
|---|---|---|
| `tripId` | `<yyyymmdd>_<HH:MM>_<feed>_<gtfs trip_id>` | `20261108_14:19_de-DELFI_3468911239` |
| `routeId` | `<feed>_<gtfs route_id>` | `de-DELFI_de:VBB:11000000\|R-Bahn\|FEX:_100` |
| `stopId`, `parentId` | `<feed>_<gtfs stop_id>` | `de-DELFI_de:11000:900003200:1:50` |
| `agencyId` | GTFS `agency_id` as is | `10434` |
| `source` | `<feed file>/stop_times.txt:<from>:<to>` | `de_DELFI.gtfs.zip/stop_times.txt:43735665:43735668` |

- The feed tag (`de-DELFI`) is everything up to the first `_` after the date
  and time prefix. The GTFS id is the rest.
- The `source` file name spells the feed with `_` in place of `-`.
- The yyyymmdd prefix of `tripId` is the GTFS service date, and
  `trip.gtfs.service_date` stores it.
- `/api/v6/trip?tripId=...` returns one itinerary whose leg has
  `intermediateStops` and `legGeometry` (encoded polyline with `precision`).
  The pipeline uses it for the trip shape.

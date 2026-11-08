# gtfs-zone-wifi-ingest

Upload service for [wifi.gtfs.zone](https://github.com/gtfs-zone/gtfs-zone-wifi-pipeline/blob/main/docs/overview.md) at `ingest.wifi.gtfs.zone`.

- Accepts anonymous session uploads from gtfs-zone-wifi-app
- Validates each session against the session JSON schema, which this repo
  owns
- Rate-limits by IP without storing it
- Writes each raw session to a private Garage bucket for
  gtfs-zone-wifi-pipeline

No database and no accounts. See the [project overview](https://github.com/gtfs-zone/gtfs-zone-wifi-pipeline/blob/main/docs/overview.md).

## API

| Method and path | Response |
|---|---|
| `POST /v1/sessions` | `201` new session, `200` session_id already stored, `400` not JSON or bad gzip, `413` over the size limit (sent or decompressed), `415` unsupported `Content-Encoding`, `422` schema errors (up to 10), `429` rate limited (with `Retry-After`) |
| `GET /healthz` | `200 {"status": "ok"}` |
| `GET /generate_204` | `204` with an empty body; the app's connectivity and captive portal probe, served over plain HTTP |

The body is a session as JSON (`schemas/session.v1.json`). Send it gzipped with
`Content-Encoding: gzip`.

Storage in the bucket:

- `raw/v<schema_version>/<yyyy>/<mm>/<dd>/<session_id>.json`: the session as
  uploaded, dated by upload time (UTC)
- `ids/<session_id>`: the raw key, so a repeat upload on a later day is
  still found

## Configuration

| Variable | Default | |
|---|---|---|
| `S3_ENDPOINT` | | S3 endpoint URL |
| `S3_BUCKET` | `wifi-raw` | |
| `S3_REGION` | `garage` | |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | | |
| `MAX_BODY_BYTES` | `2097152` | Limit on the sent and the decompressed body |
| `RATE_LIMIT`, `RATE_WINDOW_S` | `30`, `3600` | Uploads per client per window, in memory |
| `TRUSTED_PROXIES` | `127.0.0.1` | Proxies whose `X-Forwarded-For` gives the client address |
| `HOST`, `PORT` | `0.0.0.0`, `8000` | |
| `SCHEMA_DIR` | `schemas/` | Directory of `session.v<N>.json` files |

Client addresses are used only as rate limit keys (hashed with a per-process
key) and never logged. The uvicorn access log is off; the service logs
method, path, status, duration and session_id.

## Local run

Start Garage from [gtfs-zone-dev-stack](https://github.com/gtfs-zone/gtfs-zone-dev-stack)
and create the `wifi-raw` bucket for the dev key:

```bash
cd ../gtfs-zone-dev-stack
docker compose up -d garage garage-init
docker compose exec garage /garage -c /etc/garage.toml bucket create wifi-raw
docker compose exec garage /garage -c /etc/garage.toml \
  bucket allow --read --write wifi-raw --key GK0123456789abcdef01234567
```

Run the service with the dev settings:

```bash
cp .env.example .env
set -a; . ./.env; set +a
uv run gtfs-zone-wifi-ingest
```

Upload a fixture, plain and gzipped:

```bash
curl -i -H 'Content-Type: application/json' \
  --data-binary @tests/fixtures/sessions/trip-good-wifi.json \
  http://localhost:8000/v1/sessions
gzip -c tests/fixtures/sessions/station-checklist.json | curl -i \
  -H 'Content-Type: application/json' -H 'Content-Encoding: gzip' \
  --data-binary @- http://localhost:8000/v1/sessions
```

## Development

```bash
scripts/check.sh   # ruff, vulture, deptry and pytest (S3 against a moto server)
```

## License

AGPL-3.0-or-later. See [LICENSE.txt](LICENSE.txt).

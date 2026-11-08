# gtfs-zone-wifi-ingest

Upload service for [wifi.gtfs.zone](https://github.com/gtfs-zone/gtfs-zone-wifi-pipeline/blob/main/docs/overview.md) at `ingest.wifi.gtfs.zone`.

- Accepts anonymous session uploads from gtfs-zone-wifi-app
- Validates each session against the session JSON schema, which this repo
  owns
- Rate-limits by IP without storing it
- Writes each raw session to a private Garage bucket for
  gtfs-zone-wifi-pipeline

No database and no accounts. See the [project overview](https://github.com/gtfs-zone/gtfs-zone-wifi-pipeline/blob/main/docs/overview.md).

## License

AGPL-3.0-or-later. See [LICENSE.txt](LICENSE.txt).

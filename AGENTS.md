# AGENTS.md

Thin upload service for wifi.gtfs.zone (Python, runs in k3s at
`ingest.wifi.gtfs.zone`). It validates anonymous session uploads from
gtfs-zone-wifi-app, rate-limits by IP and writes raw session JSON to a
private Garage bucket read by gtfs-zone-wifi-pipeline.

- **Schema**: the session JSON schema lives here and is versioned; the app
  and pipeline pin to it.
- **Privacy**: never log or store client IPs or anything that links uploads
  to each other or to a device.
- **Scope**: validate and store only. Processing belongs in the pipeline.

## Conventions

- **Commits**: Conventional Commits, enforced by the `commit-msg` hook. Never add
  Co-Authored-By trailers. Setup is in [CONTRIBUTING.md](CONTRIBUTING.md).
- **Cross-repo work**: sibling gtfs.zone repos live under the same parent
  directory and may be read and edited when a change spans repos.
- **Plans**: the central plan is `CURRENT_PLAN.md` in gtfs-zone-wifi-pipeline
  (phases across all wifi repos). A local `CURRENT_PLAN.md` here only points
  there. It is neither tracked nor gitignored: never stage or commit it.

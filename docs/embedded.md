# Embedded Build Module

## Setup

- Initialise `embedded/` submodules (`poky`, `meta-openembedded`, `meta-petalinux`, `kas`).
- Configure `EMBEDDED_BUILD_ROOT` for build workspace.

## Endpoints

- `POST /api/embedded/build`
- `GET /api/embedded/build/{job_id}`
- `GET /api/embedded/layers`
- `POST /api/embedded/layers`
- `GET /api/embedded/artifacts`
- `GET /api/embedded/artifacts/{name}`

## Notes

Build stage transitions are logged in SQLite `embed_builds`.

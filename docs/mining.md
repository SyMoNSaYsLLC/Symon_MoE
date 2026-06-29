# Mining Module

## Setup

- Initialise submodules under `miners/`.
- Enable mining API by setting `MINING_ENABLED=true`.

## Endpoints

- `GET /api/mining/pools`
- `POST /api/mining/start`
- `POST /api/mining/stop`
- `GET /api/mining/status`
- `GET /api/mining/transactions`
- `POST /api/mining/braiins/action`
- `POST /api/mining/whatsminer/action`

## Notes

Mining worker stats are persisted to SQLite `mining_stats`.

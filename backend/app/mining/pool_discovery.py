from __future__ import annotations

from datetime import UTC, datetime

DEFAULT_POOLS = [
    {"network": "BTC", "name": "SlushPool", "fee": 2.0, "hashrate": "n/a", "stratum_url": "stratum+tcp://stratum.slushpool.com:3333"},
    {"network": "BTC", "name": "AntPool", "fee": 2.5, "hashrate": "n/a", "stratum_url": "stratum+tcp://stratum.antpool.com:3333"},
    {"network": "ETH", "name": "Ethermine Legacy", "fee": 1.0, "hashrate": "legacy", "stratum_url": "stratum+tcp://eu1.ethermine.org:4444"},
]


class PoolDiscovery:
    def __init__(self) -> None:
        self._cache = {"updated_at": None, "pools": []}

    def discover(self) -> dict:
        self._cache = {
            "updated_at": datetime.now(UTC).isoformat(),
            "pools": DEFAULT_POOLS,
        }
        return self._cache

    def get_cached(self) -> dict:
        if not self._cache["pools"]:
            return self.discover()
        return self._cache

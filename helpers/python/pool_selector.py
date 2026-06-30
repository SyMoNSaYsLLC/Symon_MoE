from __future__ import annotations


def rank_pools(pools: list[dict]) -> list[dict]:
    def score(pool: dict) -> float:
        fee = float(pool.get("fee", 0.0))
        latency = float(pool.get("latency", 50.0))
        luck = float(pool.get("luck", 1.0))
        return (100 - fee * 10) + max(0, 100 - latency) + luck * 10

    ranked = []
    for pool in pools:
        item = dict(pool)
        item["score"] = round(score(pool), 2)
        ranked.append(item)
    return sorted(ranked, key=lambda p: p["score"], reverse=True)

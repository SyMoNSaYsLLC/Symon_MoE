from __future__ import annotations


class LayerManager:
    def __init__(self) -> None:
        self._layers: list[str] = []

    def add(self, layer_url: str) -> dict:
        if layer_url not in self._layers:
            self._layers.append(layer_url)
        return {"layers": list(self._layers)}

    def list(self) -> list[str]:
        return list(self._layers)

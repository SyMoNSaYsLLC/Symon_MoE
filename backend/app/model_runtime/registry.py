from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class RegistryItem(Generic[T]):
    name: str
    value: T


class PluginRegistry(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[str, RegistryItem[T]] = {}

    def register(self, name: str, value: T) -> None:
        if name in self._items:
            raise ValueError(f"Plugin already registered: {name}")
        self._items[name] = RegistryItem(name=name, value=value)

    def get(self, name: str) -> T:
        item = self._items.get(name)
        if item is None:
            raise KeyError(f"Unknown plugin: {name}")
        return item.value

    def names(self) -> list[str]:
        return sorted(self._items.keys())

    def values(self) -> list[T]:
        return [self._items[name].value for name in sorted(self._items.keys())]


DetectorCallable = Callable[[str, list[str]], tuple[float, list[str]] | None]

DETECTOR_REGISTRY: PluginRegistry[DetectorCallable] = PluginRegistry()
LOADER_REGISTRY: PluginRegistry[str] = PluginRegistry()
CONVERTER_REGISTRY: PluginRegistry[str] = PluginRegistry()
RUNTIME_REGISTRY: PluginRegistry[str] = PluginRegistry()
TASK_PIPELINE_REGISTRY: PluginRegistry[str] = PluginRegistry()
WORKER_REGISTRY: PluginRegistry[str] = PluginRegistry()

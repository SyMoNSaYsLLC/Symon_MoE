__all__ = ["BitbakeWorker", "LayerManager", "list_profiles", "get_profile"]


def __getattr__(name: str):
    if name == "BitbakeWorker":
        from .bitbake_worker import BitbakeWorker

        return BitbakeWorker
    if name == "LayerManager":
        from .layer_manager import LayerManager

        return LayerManager
    if name in {"list_profiles", "get_profile"}:
        from .device_profiles import get_profile, list_profiles

        return {"list_profiles": list_profiles, "get_profile": get_profile}[name]
    raise AttributeError(name)

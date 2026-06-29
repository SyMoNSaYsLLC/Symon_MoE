from __future__ import annotations

import os

import psutil

CPU_LIMIT = float(os.getenv("HARDWARE_THROTTLE_CPU_LIMIT", "95"))
GPU_LIMIT = float(os.getenv("HARDWARE_THROTTLE_GPU_LIMIT", "95"))


def throttle_check() -> bool:
    cpu = psutil.cpu_percent(interval=0.1)
    # GPU metrics are optional in this environment; use env override as a soft gate.
    gpu = float(os.getenv("SYMON_GPU_LOAD", "0"))
    return cpu <= CPU_LIMIT and gpu <= GPU_LIMIT

from __future__ import annotations


def default_rootfs_config() -> dict:
    return {
        "MACHINE": "qemuarm64",
        "DISTRO": "poky",
        "IMAGE_FEATURES": ["ssh-server-dropbear"],
    }

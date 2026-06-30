def plan_cross_compile(profile: dict) -> dict:
    # TODO: Wire toolchain setup and build matrix execution.
    return {"system": "cross_compile", "target_arch": profile.get("arch"), "status": "planned"}

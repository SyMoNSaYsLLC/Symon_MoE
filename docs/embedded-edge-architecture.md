# Embedded Edge Architecture

## Overview

The embedded edge layer is isolated from model conversion and runtime inspection logic.

## New structure

- `backend/app/embedded/device_profiles/`
- `backend/app/embedded/yocto/`
- `backend/app/embedded/bitbake/`
- `backend/app/embedded/cross_compile/`
- `backend/app/embedded/deployment/`

## Device profiles

- `raspberry_pi_armv7_32bit`
- `raspberry_pi_arm64`
- `generic_openwrt`
- `antminer_linux`
- `generic_embedded_linux`
- `generic_iot_gateway`

Each profile declares architecture, machine target, toolchain, packaging artifact format, and runtime targets.

## Deployment separation

- Model conversion selection lives in `model_runtime/converter_router.py`.
- Embedded packaging decisions are tied to a selected device profile.
- Embedded pipeline modules are currently planning stubs with TODO markers for full implementation.

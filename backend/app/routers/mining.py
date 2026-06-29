from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..mining.braiins_api import run_braiins_action
from ..mining.miner_worker import MiningWorker
from ..mining.pool_discovery import PoolDiscovery
from ..mining.transaction_verifier import TransactionVerifier
from ..mining.whatsminer_api import run_whatsminer_action

router = APIRouter(prefix="/api/mining", tags=["mining"])

POOL_DISCOVERY = PoolDiscovery()
MINING_WORKER = MiningWorker()
TX_VERIFIER = TransactionVerifier()


class MiningStartRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    pool: str = Field(..., min_length=1)


class MiningStopRequest(BaseModel):
    device_id: str = Field(..., min_length=1)


class MinerActionRequest(BaseModel):
    miner_ip: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    payload: dict = {}


@router.get("/pools")
def get_pools() -> dict:
    return POOL_DISCOVERY.get_cached()


@router.post("/start")
def start_miner(request: MiningStartRequest) -> dict:
    return MINING_WORKER.start(request.device_id, request.pool)


@router.post("/stop")
def stop_miner(request: MiningStopRequest) -> dict:
    return MINING_WORKER.stop(request.device_id)


@router.get("/status")
def mining_status() -> dict:
    return {"miners": MINING_WORKER.status()}


@router.get("/transactions")
def recent_transactions() -> dict:
    return {"transactions": TX_VERIFIER.recent()}


@router.post("/braiins/action")
def braiins_action(request: MinerActionRequest) -> dict:
    return run_braiins_action(request.miner_ip, request.action, request.payload)


@router.post("/whatsminer/action")
def whatsminer_action(request: MinerActionRequest) -> dict:
    return run_whatsminer_action(request.miner_ip, request.action, request.payload)

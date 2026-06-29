from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/calc", tags=["calculator"])

# Add helpers/python to path so we can import sympy_calc
REPO_ROOT = Path(__file__).resolve().parents[4]
_HELPERS = str(REPO_ROOT / "helpers" / "python")
if _HELPERS not in sys.path:
    sys.path.insert(0, _HELPERS)

try:
    from sympy_calc import evaluate as _sympy_evaluate  # type: ignore[import-not-found]
    HAS_SYMPY_CALC = True
except ImportError:
    HAS_SYMPY_CALC = False


class CalcRequest(BaseModel):
    mode: str = "numeric"   # derivative | integral | limit | ode | numeric
    expr: str
    var: str = "x"
    # derivative
    order: int = 1
    # integral
    lower: str | None = None
    upper: str | None = None
    # limit
    point: str = "0"
    direction: str = "+"    # "+" | "-" | "+-"
    # ode
    func: str = "y"
    ics: dict[str, str] | None = None
    # numeric
    values: dict[str, float] | None = None
    precision: int = 15


@router.post("")
async def calculate(request: CalcRequest) -> dict:
    """Evaluate a mathematical expression using SymPy."""
    if not HAS_SYMPY_CALC:
        raise HTTPException(
            status_code=503,
            detail="SymPy not available. Run: pip install sympy",
        )

    try:
        result = _sympy_evaluate(request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result


@router.get("/modes")
async def list_modes() -> dict:
    """List supported calculator modes."""
    return {
        "modes": [
            {"name": "derivative", "description": "Compute d/dx f(x) (supports order parameter)"},
            {"name": "integral",   "description": "Indefinite or definite integral"},
            {"name": "limit",      "description": "Limit as variable approaches a point"},
            {"name": "ode",        "description": "Solve ordinary differential equations"},
            {"name": "numeric",    "description": "Numeric evaluation of an expression"},
        ]
    }

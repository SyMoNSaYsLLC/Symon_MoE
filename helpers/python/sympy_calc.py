#!/usr/bin/env python3
"""
sympy_calc.py — SymPy-based calculus engine for the AI calculator app.

Provides derivatives, integrals, limits, ODE solving, and numeric evaluation,
returning both LaTeX symbolic output and a decimal approximation.  Used by the
backend /api/calc endpoint.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

try:
    import sympy
    from sympy import (
        Symbol, symbols, sympify, latex, N,
        diff, integrate, limit, oo,
        dsolve, Function, Eq,
        SympifyError,
    )
    from sympy.parsing.sympy_parser import (
        parse_expr,
        standard_transformations,
        implicit_multiplication_application,
    )
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False

_TRANSFORMS = None
if HAS_SYMPY:
    _TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


def _require_sympy() -> None:
    if not HAS_SYMPY:
        raise ImportError("sympy not installed. Run: pip install sympy")


def _parse(expr_str: str, local_vars: dict | None = None) -> Any:
    """Parse an expression string to a SymPy expression."""
    _require_sympy()
    return parse_expr(expr_str, local_dict=local_vars, transformations=_TRANSFORMS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calc_derivative(
    expr_str: str,
    variable: str = "x",
    order: int = 1,
) -> dict[str, str]:
    """
    Compute the derivative of *expr_str* with respect to *variable*.

    Returns
    -------
    dict with keys: "latex", "numeric" (string), "expr" (str repr)
    """
    _require_sympy()
    var = Symbol(variable)
    expr = _parse(expr_str, {variable: var})
    result = diff(expr, var, order)
    return {
        "latex": latex(result),
        "numeric": str(N(result)),
        "expr": str(result),
    }


def calc_integral(
    expr_str: str,
    variable: str = "x",
    lower: str | None = None,
    upper: str | None = None,
) -> dict[str, str]:
    """
    Compute the indefinite or definite integral of *expr_str*.

    If *lower* and *upper* are provided, computes a definite integral.

    Returns
    -------
    dict with keys: "latex", "numeric" (for definite integrals), "expr"
    """
    _require_sympy()
    var = Symbol(variable)
    expr = _parse(expr_str, {variable: var})
    if lower is not None and upper is not None:
        lo = _parse(lower, {variable: var})
        hi = _parse(upper, {variable: var})
        result = integrate(expr, (var, lo, hi))
        numeric = str(N(result))
    else:
        result = integrate(expr, var)
        numeric = ""
    return {
        "latex": latex(result),
        "numeric": numeric,
        "expr": str(result),
    }


def calc_limit(
    expr_str: str,
    variable: str = "x",
    point: str = "0",
    direction: str = "+",
) -> dict[str, str]:
    """
    Compute lim_{variable → point} expr.

    Parameters
    ----------
    direction : '+' (right), '-' (left), or '+-' (two-sided).

    Returns
    -------
    dict with keys: "latex", "numeric", "expr"
    """
    _require_sympy()
    var = Symbol(variable)
    expr = _parse(expr_str, {variable: var})

    special = {"oo": oo, "-oo": -oo, "inf": oo, "-inf": -oo}
    pt = special.get(point.strip(), _parse(point, {variable: var}))

    if direction == "+-":
        result = limit(expr, var, pt)
    else:
        result = limit(expr, var, pt, direction)

    return {
        "latex": latex(result),
        "numeric": str(N(result)),
        "expr": str(result),
    }


def solve_ode(
    ode_str: str,
    func_name: str = "y",
    variable: str = "x",
    ics: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Solve an ODE expressed as a SymPy equation string.

    The ODE should be written in terms of *func_name*(*variable*) and its
    derivatives, e.g. ``"Eq(y(x).diff(x) + y(x), x)"`` or simply
    ``"y(x).diff(x) + y(x) - x"`` (treated as = 0 if no Eq wrapper).

    Parameters
    ----------
    ode_str   : ODE as a string expression.
    func_name : Dependent function name (default: 'y').
    variable  : Independent variable name (default: 'x').
    ics       : Initial conditions dict, e.g. {"y(0)": "1"}.

    Returns
    -------
    dict with keys: "latex", "expr", "solutions" (list of str)
    """
    _require_sympy()
    var = Symbol(variable)
    func = Function(func_name)
    local_vars: dict = {variable: var, func_name: func}

    ode_expr = _parse(ode_str, local_vars)
    if not isinstance(ode_expr, Eq):
        ode_expr = Eq(ode_expr, 0)

    parsed_ics: dict | None = None
    if ics:
        parsed_ics = {_parse(k, local_vars): _parse(v, local_vars) for k, v in ics.items()}

    sol = dsolve(ode_expr, func(var), ics=parsed_ics)
    solutions = [sol] if not isinstance(sol, list) else sol

    return {
        "latex": latex(solutions[0]),
        "expr": str(solutions[0]),
        "solutions": [str(s) for s in solutions],
    }


def numeric_evaluate(
    expr_str: str,
    variable_values: dict[str, float] | None = None,
    precision: int = 15,
) -> dict[str, str]:
    """
    Numerically evaluate *expr_str* after substituting *variable_values*.

    Returns
    -------
    dict with keys: "latex", "numeric", "expr"
    """
    _require_sympy()
    local_vars: dict = {}
    if variable_values:
        local_vars = {k: Symbol(k) for k in variable_values}
    expr = _parse(expr_str, local_vars)
    if variable_values:
        subs = {Symbol(k): v for k, v in variable_values.items()}
        expr = expr.subs(subs)
    numeric = str(N(expr, precision))
    return {
        "latex": latex(expr),
        "numeric": numeric,
        "expr": str(expr),
    }


# ---------------------------------------------------------------------------
# Unified dispatch (used by /api/calc backend)
# ---------------------------------------------------------------------------

def evaluate(request: dict) -> dict:
    """
    Unified evaluation dispatcher for the /api/calc endpoint.

    Expected request keys:
    - ``mode``  : One of 'derivative', 'integral', 'limit', 'ode', 'numeric'.
    - ``expr``  : Expression string.
    - ``var``   : Variable name (default 'x').
    - Additional mode-specific keys (see individual functions).

    Returns a dict with at least "latex", "numeric", and "expr" keys.
    """
    mode = request.get("mode", "numeric")
    expr = request.get("expr", "0")
    var = request.get("var", "x")

    if mode == "derivative":
        return calc_derivative(expr, var, int(request.get("order", 1)))
    elif mode == "integral":
        return calc_integral(expr, var, request.get("lower"), request.get("upper"))
    elif mode == "limit":
        return calc_limit(expr, var, request.get("point", "0"), request.get("direction", "+"))
    elif mode == "ode":
        return solve_ode(expr, request.get("func", "y"), var, request.get("ics"))
    else:  # numeric / default
        return numeric_evaluate(expr, request.get("values"), int(request.get("precision", 15)))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SymPy calculus engine")
    parser.add_argument("mode", choices=["derivative", "integral", "limit", "ode", "numeric"])
    parser.add_argument("expr", help="Expression to evaluate")
    parser.add_argument("--var", default="x")
    parser.add_argument("--order", type=int, default=1, help="Derivative order")
    parser.add_argument("--lower", default=None, help="Integral lower bound")
    parser.add_argument("--upper", default=None, help="Integral upper bound")
    parser.add_argument("--point", default="0", help="Limit point")
    parser.add_argument("--direction", default="+", choices=["+", "-", "+-"])
    parser.add_argument("--func", default="y", help="ODE dependent function name")
    parser.add_argument("--precision", type=int, default=15)
    args = parser.parse_args()

    req = {
        "mode": args.mode,
        "expr": args.expr,
        "var": args.var,
        "order": args.order,
        "lower": args.lower,
        "upper": args.upper,
        "point": args.point,
        "direction": args.direction,
        "func": args.func,
        "precision": args.precision,
    }
    result = evaluate(req)
    print(json.dumps(result, indent=2))

#!/usr/bin/env python3
"""Simple Flask API exposing a stub equation solver."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from flask import Flask, jsonify, request
from sympy import Eq, solve, sympify
from sympy.core.symbol import Symbol
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# Pre-compute transformations for better performance
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
)


@lru_cache(maxsize=256)
def parse_equation(equation_str: str) -> tuple[Any, frozenset[Symbol]]:
    """Parse equation string and return sympy expression with variables.

    Cached for performance on repeated queries.
    """
    expr = parse_expr(equation_str, transformations=TRANSFORMATIONS)
    return expr, frozenset(expr.free_symbols)


@lru_cache(maxsize=128)
def _solve_cached(
    equation_str: str,
) -> str:
    """Internal cached solver for immutable inputs."""
    # Check if equation contains '=' (is an equation)
    if "=" in equation_str:
        left, right = equation_str.split("=", 1)
        left_expr, left_symbols = parse_equation(left.strip())
        right_expr, right_symbols = parse_equation(right.strip())
        expr = Eq(left_expr, right_expr)
        free_symbols = left_symbols | right_symbols
    else:
        # Treat as expression to solve for 0
        expr, free_symbols = parse_equation(equation_str)

    if not free_symbols:
        # No variables, just evaluate - fast path
        result = sympify(expr)
        return f"result:{result}"

    # Solve for the first variable (or all if multiple)
    symbols_list = sorted(free_symbols, key=lambda s: str(s))
    variable = symbols_list[0] if len(symbols_list) == 1 else None

    if variable:
        solutions = solve(expr, variable, dict=False)
        if not solutions:
            return "result:No solution found"
        if isinstance(solutions, list):
            formatted = ", ".join(str(sol) for sol in solutions)
            return f"result:{variable} = {formatted}"
        return f"result:{variable} = {solutions}"
    else:
        # Multiple variables
        solutions = solve(expr, free_symbols, dict=True)
        if not solutions:
            return "result:No solution found"
        return f"result:{solutions}"


def solve_equation(
    equation_str: str,
) -> dict[str, str | list[str]]:
    """Solve equation and return result or error."""
    try:
        result = _solve_cached(equation_str)
        if result.startswith("result:"):
            return {"result": result[7:]}
        return {"error": result}
    except (ValueError, SyntaxError, TypeError) as e:
        return {"error": f"Invalid equation format: {str(e)}"}
    except Exception as e:
        return {"error": f"Error solving equation: {str(e)}"}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.after_request
    def add_cors_headers(response):  # type: ignore[override]
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.get("/solve")
    def solve_endpoint():
        equation = (request.args.get("equation") or "").strip()
        if not equation:
            return jsonify({"error": "Missing 'equation' query parameter"}), 400

        result = solve_equation(equation)
        status_code = 400 if "error" in result else 200
        return jsonify(result), status_code

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({"message": "Equation API. Try /solve?equation=1+1"})

    return app


def run() -> None:
    port = int(os.environ.get("PORT", 8000))
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run()

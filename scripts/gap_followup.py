#!/usr/bin/env python3
"""Calculate the recorded six-case gap follow-up from retained estimates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


CASES = (
    "primary", "six_lags", "poor_man", "pre_pandemic",
    "short_bandwidth", "long_bandwidth",
)
R_COLUMNS = (
    "case", "n", "p_weight", "p_theta", "p_IUT",
    "ellipse95_low", "ellipse95_high",
)
REL_TOL = 1e-10
ABS_TOL = 1e-12
ALPHA = 0.05
ELLIPSE_LEVEL = 0.95


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_float(value: Any, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite value for {label}")
    return number


def normal_p(estimate: float, standard_error: float) -> tuple[float, float]:
    if standard_error <= 0:
        raise ValueError("Marginal standard errors must be strictly positive")
    z = estimate / standard_error
    return z, math.erfc(abs(z) / math.sqrt(2.0))


def ellipse_product_bounds(
    weight: float, theta: float, weight_se: float, theta_se: float,
    covariance: float,
) -> dict[str, Any]:
    """Project the positive-definite two-coordinate 95% Wald ellipse."""
    if weight_se <= 0 or theta_se <= 0:
        raise ValueError("Ellipse coordinates require positive standard errors")
    variance = np.array(
        [[weight_se**2, covariance], [covariance, theta_se**2]],
        dtype=float,
    )
    if not np.isfinite(variance).all():
        raise ValueError("Non-finite two-coordinate covariance")
    try:
        chol = np.linalg.cholesky(variance)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Two-coordinate covariance is singular or not positive definite; "
            "no ridge or reduced-rank substitution is permitted"
        ) from exc

    # For two degrees of freedom, the chi-square survival function is exp(-x/2).
    critical = -2.0 * math.log(1.0 - ELLIPSE_LEVEL)
    scaled = math.sqrt(critical) * chol
    a, b = weight, theta
    A, C, D = float(scaled[0, 0]), float(scaled[1, 0]), float(scaled[1, 1])
    K, L = a * C + b * A, a * D
    coefficients = np.array(
        [L + A * D, -2 * K - 4 * A * C, -6 * A * D,
         -2 * K + 4 * A * C, -L + A * D],
        dtype=float,
    )
    polynomial_scale = float(np.max(np.abs(coefficients)))
    if not math.isfinite(polynomial_scale) or polynomial_scale == 0:
        raise ValueError("Degenerate ellipse stationary polynomial")
    roots = np.polynomial.polynomial.polyroots(coefficients / polynomial_scale)
    derivative_scale = max(
        abs(K) + abs(L) + 2 * abs(A * C) + 2 * abs(A * D),
        np.finfo(float).tiny,
    )

    def derivative(phi: float) -> float:
        return (-K * math.sin(phi) + L * math.cos(phi)
                - A * C * math.sin(2 * phi) + A * D * math.cos(2 * phi))

    def second_derivative(phi: float) -> float:
        return (-K * math.cos(phi) - L * math.sin(phi)
                - 2 * A * C * math.cos(2 * phi)
                - 2 * A * D * math.sin(2 * phi))

    def boundary_point(phi: float) -> np.ndarray:
        return np.array(
            [a + A * math.cos(phi), b + C * math.cos(phi) + D * math.sin(phi)]
        )

    # phi=pi is omitted by the finite half-angle parameterisation.
    angles = [math.pi]
    real_count = 0
    for root in roots:
        if abs(float(root.imag)) > 1e-9 * (1.0 + abs(float(root.real))):
            continue
        real_count += 1
        phi = 2.0 * math.atan(float(root.real))
        for _ in range(8):
            first = derivative(phi)
            if abs(first) <= 32 * np.finfo(float).eps * derivative_scale:
                break
            second = second_derivative(phi)
            if abs(second) <= 32 * np.finfo(float).eps * derivative_scale:
                break
            step = first / second
            if abs(step) > 0.25:
                raise ValueError("Stationary-root refinement is not locally stable")
            phi -= step
        if abs(derivative(phi)) / derivative_scale > 1e-9:
            raise ValueError("Half-angle candidate fails stationarity verification")
        angles.append(phi)
    pi_stationary = abs(derivative(math.pi)) / derivative_scale <= 1e-9
    if real_count + int(pi_stationary) < 2:
        raise ValueError("Fewer than two stationary boundary candidates found")

    candidates: list[tuple[float, float]] = []
    maximum_boundary_error = 0.0
    for phi in angles:
        point = boundary_point(phi)
        whitened = np.linalg.solve(chol, point - np.array([a, b]))
        distance = float(whitened @ whitened)
        boundary_error = abs(distance - critical)
        maximum_boundary_error = max(maximum_boundary_error, boundary_error)
        if not math.isclose(distance, critical, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("Ellipse candidate fails boundary verification")
        candidates.append((float(point[0] * point[1]), phi))
    lower, lower_phi = min(candidates)
    upper, upper_phi = max(candidates)
    lower_stationarity = abs(derivative(lower_phi)) / derivative_scale
    upper_stationarity = abs(derivative(upper_phi)) / derivative_scale
    if max(lower_stationarity, upper_stationarity) > 1e-9:
        raise ValueError("Selected product bound is not a stationary boundary point")
    if not (math.isfinite(lower) and math.isfinite(upper) and lower <= upper):
        raise ValueError("Invalid ellipse bounds")
    return {
        "ellipse95_low": lower,
        "ellipse95_high": upper,
        "ellipse95_zero_included": lower <= 0.0 <= upper,
        "ellipse_qc": {
            "real_stationary_roots": real_count,
            "minimum_stationarity_scaled": lower_stationarity,
            "maximum_stationarity_scaled": upper_stationarity,
            "maximum_boundary_error": maximum_boundary_error,
        },
    }


def calculate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    plan_path = root / "docs/gap_followup_specification.json"
    primary_path = root / "docs/primary_specification.json"
    estimates_path = root / "results/estimates.csv"
    plan = json.loads(plan_path.read_text())
    if plan.get("status") != "post_estimation_followup":
        raise ValueError("The follow-up must be explicitly post-estimation")
    if plan.get("cases") != list(CASES):
        raise ValueError("Follow-up plan must retain the complete canonical case order")
    primary_hash, estimates_hash = sha256(primary_path), sha256(estimates_path)
    if plan.get("primary_specification_sha256") != primary_hash:
        raise ValueError("Primary specification differs from the recorded follow-up")
    if plan.get("estimates_sha256") != estimates_hash:
        raise ValueError("Retained estimates differ from the recorded follow-up")
    if float(plan["intersection_union_test"]["alpha"]) != ALPHA:
        raise ValueError("Unexpected IUT level")
    if float(plan["joint_ellipse"]["coverage"]) != ELLIPSE_LEVEL:
        raise ValueError("Unexpected joint ellipse coverage")

    with estimates_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    output_cases = []
    for case in CASES:
        matching = [row for row in rows if row["case"] == case]
        if len(matching) != 1:
            raise ValueError(f"Expected exactly one retained row for {case}")
        row = matching[0]
        if int(row["horizon"]) != 12:
            raise ValueError(f"Non-twelve-month row for {case}")
        n = int(row["n"])
        if n <= int(row["full_rank"]):
            raise ValueError(f"Insufficient observations for {case}")
        values = {
            key: finite_float(row[key], f"{case}.{key}")
            for key in (
                "weight", "weight_se", "theta", "theta_se",
                "covariance_weight_theta", "delta", "delta_product_low",
                "delta_product_high",
            )
        }
        z_weight, p_weight = normal_p(values["weight"], values["weight_se"])
        z_theta, p_theta = normal_p(values["theta"], values["theta_se"])
        bounds = ellipse_product_bounds(
            values["weight"], values["theta"], values["weight_se"],
            values["theta_se"], values["covariance_weight_theta"],
        )
        output_cases.append({
            "case": case, "horizon": 12, "n": n,
            "first": row["first"], "last": row["last"],
            "lags": int(row["lags"]), "bandwidth": int(row["bandwidth"]),
            **values,
            "z_weight": z_weight, "z_theta": z_theta,
            "p_weight": p_weight, "p_theta": p_theta,
            "p_IUT": max(p_weight, p_theta), **bounds,
        })
    return {
        "version": 1,
        "status": "post_estimation_followup",
        "followup_specification_sha256": sha256(plan_path),
        "primary_specification_sha256": primary_hash,
        "estimates_sha256": estimates_hash,
        "methods": {
            "marginals": "Two-sided asymptotic normal p-values with retained HAC SEs",
            "iut_alpha": ALPHA,
            "iut_p_value": "max(p_weight,p_theta)",
            "ellipse_coverage": ELLIPSE_LEVEL,
            "ellipse_degrees_of_freedom": 2,
            "ellipse_critical_value": -2 * math.log(1 - ELLIPSE_LEVEL),
            "ellipse_optimisation": "All real half-angle quartic roots plus phi=pi",
        },
        "cases": output_cases,
    }


def compare_objects(actual: Any, expected: Any, label: str = "result") -> int:
    """Compare metadata exactly and all retained numeric fields tolerantly."""
    if isinstance(actual, dict):
        if not isinstance(expected, dict) or actual.keys() != expected.keys():
            raise ValueError(f"Different field set at {label}")
        return sum(compare_objects(actual[k], expected[k], f"{label}.{k}") for k in actual)
    if isinstance(actual, list):
        if not isinstance(expected, list) or len(actual) != len(expected):
            raise ValueError(f"Different list length at {label}")
        return sum(compare_objects(a, b, f"{label}[{i}]")
                   for i, (a, b) in enumerate(zip(actual, expected)))
    if isinstance(actual, bool) or isinstance(actual, str) or actual is None:
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError(f"Different metadata at {label}")
        return 0
    if isinstance(actual, (int, float)):
        if isinstance(expected, bool) or not isinstance(expected, (int, float)):
            raise ValueError(f"Non-numeric retained field at {label}")
        if not math.isfinite(float(expected)) or not math.isclose(
            float(actual), float(expected), rel_tol=REL_TOL, abs_tol=ABS_TOL
        ):
            raise ValueError(f"Numeric mismatch at {label}: {actual} versus {expected}")
        return 1
    raise ValueError(f"Unsupported result type at {label}")


def compare_r(result: dict[str, Any], path: Path) -> int:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(R_COLUMNS):
            raise ValueError(f"R CSV columns must be {list(R_COLUMNS)}")
        rows = list(reader)
    if [row["case"] for row in rows] != list(CASES):
        raise ValueError("R CSV must contain every case once in canonical order")
    comparisons = 0
    for actual, reference in zip(result["cases"], rows):
        if finite_float(reference["n"], f"{actual['case']}.n") != actual["n"]:
            raise ValueError(f"R sample mismatch for {actual['case']}")
        for key in R_COLUMNS[2:]:
            expected = finite_float(reference[key], f"{actual['case']}.{key}")
            if not math.isclose(actual[key], expected, rel_tol=REL_TOL, abs_tol=ABS_TOL):
                raise ValueError(
                    f"R mismatch for {actual['case']}.{key}: {actual[key]} versus {expected}"
                )
            comparisons += 1
    return comparisons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path,
                        help="Default: ROOT/results/gap_followup.json")
    parser.add_argument("--check", action="store_true",
                        help="Recalculate and compare the retained output without writing")
    parser.add_argument("--compare-r", type=Path,
                        help="Compare an independent six-case R CSV without writing")
    args = parser.parse_args()
    result = calculate(args.root)
    output = args.output or args.root / "results/gap_followup.json"
    if args.check:
        retained = json.loads(output.read_text())
        comparisons = compare_objects(result, retained)
        print(f"Retained follow-up matches: {comparisons} numeric fields, six cases")
    if args.compare_r:
        comparisons = compare_r(result, args.compare_r)
        print(f"Independent R follow-up matches: {comparisons} numeric fields, six cases")
    if not args.check and not args.compare_r:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        print(f"Wrote six-case follow-up: {output}")


if __name__ == "__main__":
    main()

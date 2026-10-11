"""Causal loading sensitivity and predetermined-outcome diagnostics."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import chi2, norm
from scipy.optimize import brentq


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path) -> dict:
    sys.path.insert(0, str(root / "scripts"))
    from local_projections import (
        build_design, calendar_hac, load_panel, ols, product_interval,
    )

    specification_path = root / "docs/extension_specification.json"
    spec = json.loads(specification_path.read_text())
    if (spec.get("status") != "declared_post_estimation_extension"
            or spec.get("version") != 1
            or hash_file(root / "docs/primary_specification.json") != spec["primary_specification_sha256"]
            or hash_file(root / "results/estimates.csv") != spec["estimates_sha256"]):
        raise ValueError("A dated extension and unchanged locked primary evidence are required")
    if datetime.fromisoformat(spec["recorded_utc"]) >= datetime.now(timezone.utc):
        raise ValueError("The extension record must precede its execution")
    panel_path = root / "data/processed/monthly_panel.csv"
    primary_summary = json.loads((root / "results/summary.json").read_text())
    if hash_file(panel_path) != primary_summary["panel_sha256"]:
        raise ValueError("The retained primary panel is required")
    panel = load_panel(panel_path)
    design = build_design(panel, 12, 12, "2000-01", "2025-08", "median", .1)
    x = np.column_stack([design.m, design.c, design.z])
    b, residuals, operator, _ = ols(x, design.y)
    n, k = x.shape
    if (n, k) != (308, 74):
        raise ValueError("The unchanged primary design is required")
    correction = n / (n-k)
    score = operator[:, :2] * residuals[:, None]
    covariance = calendar_hac(score, design.calendar, 18, correction)
    if np.min(np.linalg.eigvalsh(covariance)) <= 0:
        raise ValueError("Nondegenerate joint coefficient inference required")
    xr = np.column_stack([design.m + design.c, design.z])
    br, er, lr, _ = ols(xr, design.y)
    bw, ew, _, _ = ols(xr, design.c)
    weight, theta, gamma = float(bw[0]), float(b[1]-b[0]), float(br[0])
    joint_scores = np.column_stack([
        lr[:, 0]*ew, score[:, 1]-score[:, 0], lr[:, 0]*er-score[:, 0],
    ])
    joint_cov = calendar_hac(joint_scores, design.calendar, 18, correction)
    se_w, se_theta = np.sqrt(np.diag(joint_cov)[:2])
    primary = primary_summary["primary"]
    comparisons = {"beta_m": b[0], "beta_c": b[1], "gamma": gamma,
                   "weight": weight, "theta": theta}
    if not all(np.isclose(value, primary[name], atol=1e-11, rtol=1e-11)
               for name, value in comparisons.items()):
        raise ValueError("Primary reconstruction differs from retained evidence")
    z = norm.ppf(.975)
    ellipse_critical = np.sqrt(chi2.ppf(.95, 2))

    def loading_row(a: float) -> dict:
        v = np.array([1-a, a])
        response = float(v @ b[:2])
        se = float(np.sqrt(v @ covariance @ v))
        gap = gamma - response
        bounds = product_interval(weight-a, theta, float(se_w), float(se_theta))
        if not np.isclose(gap, (weight-a)*theta, atol=1e-11, rtol=1e-11):
            raise ValueError("Causal loading contrast identity failed")
        return {"a": float(a), "conditional_policy_response": response,
                "policy_response_se": se,
                "conditional_pointwise_95_low": response-z*se,
                "conditional_pointwise_95_high": response+z*se,
                "simultaneous_policy_95_low": response-ellipse_critical*se,
                "simultaneous_policy_95_high": response+ellipse_critical*se,
                "conditional_recomposed_minus_policy": float(gap),
                "simultaneous_gap_95_low": float(bounds[0]),
                "simultaneous_gap_95_high": float(bounds[1])}

    frontier = [loading_row(a) for a in np.linspace(0, 1, 101)]
    benchmarks = [loading_row(a) for a in [0, .1, .25, .5, 1]]
    envelopes = []
    for a_first, a_last in [[0,0],[0,.1],[0,.25],[0,.5],[0,1],[-.1,.1],[-.25,.25]]:
        rows = [loading_row(a_first), loading_row(a_last)]
        # An affine mean plus or minus a norm is respectively convex or concave.
        # Its extrema over a closed interval therefore occur at the endpoints.
        policy_low = min(row["simultaneous_policy_95_low"] for row in rows)
        policy_high = max(row["simultaneous_policy_95_high"] for row in rows)
        gap_low = min(row["simultaneous_gap_95_low"] for row in rows)
        gap_high = max(row["simultaneous_gap_95_high"] for row in rows)
        for bias in [0, .1, .25, .5]:
            envelopes.append({
                "a_first": a_first, "a_last": a_last,
                "externally_imposed_absolute_bias_bound": bias,
                "policy_sampling_envelope_low": policy_low-bias,
                "policy_sampling_envelope_high": policy_high+bias,
                "causal_adjustment_sampling_envelope_low": gap_low-bias,
                "causal_adjustment_sampling_envelope_high": gap_high+bias,
            })

    index_by_date = {date: i for i, date in enumerate(panel["dates"])}
    indices = np.array([index_by_date[date] for date in design.dates])
    if np.min(indices) < 26:
        raise ValueError("The declared predetermined outcome is unavailable")
    yd = 100*(np.log(panel["durable_index"][indices-13])
              - np.log(panel["durable_index"][indices-26]))
    yn = 100*(np.log(panel["nondurable_index"][indices-13])
              - np.log(panel["nondurable_index"][indices-26]))
    placebo_b, placebo_e, placebo_l, _ = ols(x, np.column_stack([yd, yn, yd-yn]))
    placebo_scores = np.column_stack([
        placebo_l[:, component]*placebo_e[:, outcome]
        for outcome in range(3) for component in range(2)
    ])
    placebo_cov = calendar_hac(placebo_scores, design.calendar, 18, correction)
    placebo = []
    for j, name in enumerate(["durable", "nondurable", "durable_minus_nondurable"]):
        estimate = placebo_b[:2, j]
        covariance_j = placebo_cov[2*j:2*j+2, 2*j:2*j+2]
        if np.min(np.linalg.eigvalsh(covariance_j)) <= 0:
            raise ValueError("Nondegenerate predetermined-outcome inference required")
        wald = float(estimate @ np.linalg.solve(covariance_j, estimate))
        p_value = float(chi2.sf(wald, 2))
        se = np.sqrt(np.diag(covariance_j))
        placebo.append({"outcome": name, "coefficient_policy": float(estimate[0]),
                        "coefficient_information": float(estimate[1]),
                        "standard_error_policy": float(se[0]),
                        "standard_error_information": float(se[1]),
                        "policy_pointwise_95_low": float(estimate[0]-z*se[0]),
                        "policy_pointwise_95_high": float(estimate[0]+z*se[0]),
                        "information_pointwise_95_low": float(estimate[1]-z*se[1]),
                        "information_pointwise_95_high": float(estimate[1]+z*se[1]),
                        "covariance": covariance_j.tolist(),
                        "wald_two_degrees_freedom": wald,
                        "p_value": p_value,
                        "bonferroni_three_outcomes_p_value": min(1., 3*p_value)})
    if not np.allclose(placebo_b[:,2], placebo_b[:,0]-placebo_b[:,1], atol=1e-10):
        raise ValueError("Predetermined sector contrast failed")

    result = {
        "author": "Amanjeet Singh", "executed_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Post-primary causal sensitivity and predetermined-outcome falsification",
        "extension_specification_sha256": hash_file(specification_path),
        "primary_specification_sha256": hash_file(root / "docs/primary_specification.json"),
        "primary_estimates_sha256": hash_file(root / "results/estimates.csv"),
        "panel_sha256": hash_file(panel_path),
        "n": n, "full_rank": k, "bandwidth": 18,
        "finite_sample_multiplier": correction,
        "primary_coefficients": {key: float(value) for key, value in comparisons.items()},
        "primary_policy_information_covariance": covariance.tolist(),
        "weight_theta_gap_covariance": joint_cov.tolist(),
        "policy_joint_ellipse_squared_critical": float(chi2.ppf(.95, 2)),
        "loadings_benchmarks": benchmarks,
        "loadings_frontier": frontier,
        "sensitivity_envelopes": envelopes,
        "point_estimate_zero_policy_loading": float(-b[0]/theta),
        "conditional_pointwise_upper_bound_zero_loading": float(brentq(
            lambda a: loading_row(a)["conditional_pointwise_95_high"], 0, 1)),
        "pointwise_zero_loading_adverse_bias_tolerance": float(-loading_row(0)["conditional_pointwise_95_high"]),
        "point_estimate_zero_causal_adjustment_loading": weight,
        "predetermined_outcome_definition": "100*(log(P[t-13])-log(P[t-26]))",
        "predetermined_outcome_results": placebo,
        "predetermined_outcome_joint_covariance": placebo_cov.tolist(),
        "interpretation": [
            "The loading fraction a is a causal direction coordinate whose value and support are not identified by these data; signed values are possible without further restrictions.",
            "The zero-error causal mapping requires a constant invertible noiseless shock measurement map, residual orthogonality and invariant responses to interventions.",
            "A classical noisy measurement map generally attenuates or mixes the coefficients and invalidates the simple zero-error mapping.",
            "The bias allowance is externally imposed sensitivity, not estimated evidence that the identifying moment holds.",
            "The joint coefficient ellipse gives a simultaneous asymptotic band for all a. Pointwise benchmark intervals cannot be interpreted as a simultaneous band.",
            "The original joint Bonferroni rectangle for weight and coefficient difference gives a simultaneous asymptotic causal-adjustment envelope for all imposed a and bias bounds.",
            "All coverage statements inherit the primary score limit and HAC assumptions, conditional on the supplied rotation, source vintage and design.",
            "Predetermined outcomes use retrospectively revised data; their tests do not replicate the real-time public information set.",
            "Non-rejection of the predetermined-outcome family does not prove exclusion, and a rejection does not uniquely identify its source.",
            "No independent excluded instrument or public-news forecast-surprise measure has been supplied; these calculations do not establish an unconditional causal effect.",
        ],
    }
    return result


def compare_nested(actual, expected, path="result") -> int:
    if isinstance(actual, dict):
        if not isinstance(expected, dict) or actual.keys() != expected.keys():
            raise ValueError(f"Different object fields at {path}")
        return sum(compare_nested(value, expected[key], f"{path}.{key}")
                   for key, value in actual.items() if key != "executed_utc")
    if isinstance(actual, list):
        if not isinstance(expected, list) or len(actual) != len(expected):
            raise ValueError(f"Different list dimensions at {path}")
        return sum(compare_nested(value, reference, f"{path}[{i}]")
                   for i, (value, reference) in enumerate(zip(actual, expected)))
    if isinstance(actual, (int, float)) and not isinstance(actual, bool):
        if (not isinstance(expected, (int, float))
                or not np.isclose(actual, expected, atol=1e-10, rtol=1e-9)):
            raise ValueError(f"Different numerical result at {path}: {actual} versus {expected}")
        return 1
    if actual != expected:
        raise ValueError(f"Different factual value at {path}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.output or args.root / "results/causal_sensitivity.json"
    result = run(args.root)
    if args.check:
        expected = json.loads(output.read_text())
        comparisons = compare_nested(result, expected)
        print(json.dumps({"status": "passed", "numeric_comparisons": comparisons}))
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
        print(json.dumps({"benchmarks": result["loadings_benchmarks"],
                          "predetermined_outcomes": result["predetermined_outcome_results"]}, indent=2))

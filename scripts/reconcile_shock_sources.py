"""Reconcile retained ECB shock files against privately retained source evidence.

This audit does not fetch data, modify raw bytes, infer policy effects or treat
agreement with the author's implementation as proof of identification.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import posixpath
from xml.etree import ElementTree as ET
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
XML_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": XML_MAIN}
FIELDS = {
    "pc1": "pc1_hf", "STOXX50": "STOXX50_hf", "MP_pm": "MP_pm",
    "CBI_pm": "CBI_pm", "MP_median": "MP_median", "CBI_median": "CBI_median",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No observations: {path}")
    return rows


def read_workbook(path: Path) -> dict[str, list[dict]]:
    """Read cached XLSX values, including mixed Excel serial and string dates."""
    result = {}
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        properties = workbook.find("m:workbookPr", NS)
        if properties is not None and properties.attrib.get("date1904") in {"1", "true"}:
            raise ValueError("The audit supports the Excel 1900 date system only")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(node.itertext()) for node in
                       ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {node.attrib["Id"]: node.attrib["Target"] for node in relationships}
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            target = targets[sheet.attrib[f"{{{XML_REL}}}id"]]
            internal = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            root = ET.fromstring(archive.read(internal))
            rows = []
            for row in root.findall("m:sheetData/m:row", NS):
                values = {}
                for cell in row:
                    column = cell.attrib["r"].rstrip("0123456789")
                    value = cell.find("m:v", NS)
                    cell_type = cell.attrib.get("t")
                    if cell_type == "inlineStr":
                        values[column] = "".join(cell.find("m:is", NS).itertext())
                    elif value is not None:
                        if cell_type == "s":
                            values[column] = strings[int(value.text)]
                        elif cell_type in {"str", "e"}:
                            values[column] = value.text
                        else:
                            values[column] = Decimal(value.text)
                if values:
                    rows.append(values)
            result[sheet.attrib["name"]] = rows
    return result


def event_date(value) -> str:
    if isinstance(value, Decimal):
        if value != int(value):
            raise ValueError("An event date contains a time of day")
        return (date(1899, 12, 30) + timedelta(days=int(value))).isoformat()
    if isinstance(value, str):
        return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
    raise ValueError(f"Unsupported event date: {value!r}")


def calendar(first: str, last: str) -> list[str]:
    start = date.fromisoformat(first + "-01")
    end = date.fromisoformat(last + "-01")
    return [f"{i // 12:04d}-{i % 12 + 1:02d}" for i in
            range(start.year * 12 + start.month - 1, end.year * 12 + end.month)]


def construction_check(raw: dict, events: list[dict]) -> dict:
    """Independently compute the uncentred PCA and median admissible rotation."""
    import numpy as np

    dates = [row["date"] for row in events]
    ir_names = ["OIS_1M", "OIS_3M", "OIS_6M", "OIS_1Y"]
    X = np.array([[float(raw[d][name]) if name in raw[d] else np.nan
                   for name in ir_names] for d in dates])
    entirely_missing = np.isnan(X).all(axis=1)
    filled = np.where(np.isnan(X), 0.0, X)
    scale = filled.std(axis=0, ddof=1)
    if np.any(~np.isfinite(scale)) or np.any(scale <= 0):
        raise ValueError("Invalid standardisation scale")
    Z = filled / scale
    eigenvalues, eigenvectors = np.linalg.eigh(Z.T @ Z)
    loading = eigenvectors[:, -1]
    # PCA's sign is arbitrary; choose a positive one-year-rate loading.
    if loading[-1] < 0:
        loading = -loading
    score = Z @ loading
    score[entirely_missing] = np.nan
    pc = score / np.nanstd(score, ddof=1) * np.nanstd(X[:, -1], ddof=1) / 100
    retained_pc = np.array([float(row["pc1"]) for row in events])
    rounded_pc = np.round(pc, 8)
    pc_error = np.abs(rounded_pc - retained_pc)
    pc_tol = 1e-8

    stock = np.array([float(raw[d]["STOXX50"]) if "STOXX50" in raw[d] else np.nan
                      for d in dates])
    M = np.column_stack((retained_pc, stock))
    complete = np.isfinite(M).all(axis=1)
    Q, R = np.linalg.qr(M[complete], mode="reduced")
    signs = np.diag(np.sign(np.diag(R)))
    Q, R = Q @ signs, signs @ R
    if R[0, 1] > 0:
        angle = 0.5 * math.atan(R[0, 1] / R[1, 1]) + 0.5 * math.pi / 2
    else:
        angle = 0.5 * math.atan(-R[1, 1] / R[0, 1])
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.array([[c, s], [-s, c]])
    normalisation = np.diag([R[0, 0] * c, R[0, 0] * s])
    shocks = Q @ rotation @ normalisation
    effects = np.linalg.solve(normalisation, rotation.T @ R)
    retained_median = np.array([[float(row["MP_median"]), float(row["CBI_median"])]
                                for row in events])[complete]
    median_error = np.abs(np.round(shocks, 8) - retained_median)
    if not np.all(complete):
        raise ValueError("Cannot certify construction with missing factor or equity rows")
    return {
        "numpy_version": np.__version__,
        "method": "Symmetric eigendecomposition of uncentred standardised X'X, then QR median rotation",
        "pca_sign_convention": "Positive loading on the one-year OIS input; principal-component sign is arbitrary",
        "pca_largest_eigenvalue": float(eigenvalues[-1]),
        "pca_loadings": dict(zip(ir_names, map(float, loading))),
        "pc1_max_abs_difference_after_eight_decimal_rounding": float(pc_error.max()),
        "pc1_tolerance": pc_tol,
        "pc1_matches": bool(np.all(pc_error <= pc_tol)),
        "median_angle_radians": angle,
        "median_effects_on_equity": {"MP": float(effects[0, 1]), "CBI": float(effects[1, 1])},
        "median_max_abs_difference_after_eight_decimal_rounding": float(median_error.max()),
        "median_tolerance": 1e-8,
        "median_matches": bool(np.all(median_error <= 1e-8)),
        "median_shock_uncentred_cross_product": float(shocks[:, 0] @ shocks[:, 1]),
        "limits": "This is a numerical construction check, not a causal-identification test or a replication of the article's macroeconometric results.",
    }


def audit(snapshot: Path, evidence: Path, metadata_path: Path, recreate: bool = True) -> dict:
    manifest = json.loads((snapshot / "manifest.json").read_text())
    for source in manifest["sources"]:
        if digest(snapshot / source["file"]) != source["sha256"]:
            raise ValueError(f"Retained raw hash differs: {source['file']}")
    metadata = json.loads(metadata_path.read_text())
    sources = {source["role"]: source for source in metadata["sources"]}
    for source in metadata["sources"]:
        path = evidence / source["file"]
        if not path.resolve().is_relative_to(evidence.resolve()):
            raise ValueError("Source metadata contains a path outside the evidence directory")
        if digest(path) != source["sha256"] or path.stat().st_size != source["bytes"]:
            raise ValueError(f"Source-review evidence hash differs: {source['file']}")
    workbook = evidence / sources["raw_ea_mpd_workbook"]["file"]
    exclusions = {entry["date"]: entry["reason"] for entry in metadata["excluded_events"]}
    events = read_csv(snapshot / "jk_ecb_events.csv")
    monthly = read_csv(snapshot / "jk_ecb_monthly.csv")
    dates = [date.fromisoformat(row["date"]).isoformat() for row in events]
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError("Event dates must be unique and ordered")
    months = [f"{int(row['year']):04d}-{int(row['month']):02d}" for row in monthly]
    if months != calendar(dates[0][:7], dates[-1][:7]):
        raise ValueError("Monthly file differs from the event-span calendar")
    for row in events + monthly:
        for field, value in row.items():
            if field not in {"date", "year", "month"} and not Decimal(value).is_finite():
                raise ValueError(f"Missing or invalid supplied value: {field}")

    workbook_data = read_workbook(workbook)
    coverage = {}
    raw = {}
    for name in ["Press Release Window", "Press Conference Window", "Monetary Event Window"]:
        rows = workbook_data[name]
        header = rows[0]
        parsed = {}
        serial_dates = string_dates = 0
        for row in rows[1:]:
            if "A" not in row:
                continue
            d = event_date(row["A"])
            serial_dates += isinstance(row["A"], Decimal)
            string_dates += isinstance(row["A"], str)
            if d in parsed:
                raise ValueError(f"Duplicate source event date in {name}: {d}")
            parsed[d] = {header[col]: value for col, value in row.items() if col in header and col != "A"}
        coverage[name] = {"dated_rows": len(parsed), "first": min(parsed), "last": max(parsed),
                          "serial_date_cells": serial_dates, "text_date_cells": string_dates}
        if name == "Monetary Event Window":
            raw = parsed
    missing_derived = sorted(set(raw) - set(dates))
    unexpected_derived = sorted(set(dates) - set(raw))
    if missing_derived != sorted(exclusions) or unexpected_derived:
        raise ValueError("Source-to-derived date mismatch is not exactly the documented exclusions")

    sums = defaultdict(lambda: defaultdict(Decimal))
    counts = Counter(d[:7] for d in dates)
    for row in events:
        for source_field, monthly_field in FIELDS.items():
            sums[row["date"][:7]][monthly_field] += Decimal(row[source_field])
    aggregation = {}
    for field in FIELDS.values():
        tolerance = Decimal("1e-12") if field == "STOXX50_hf" else Decimal("1e-15")
        differences = [(month, abs(Decimal(row[field]) - sums[month][field]))
                       for month, row in zip(months, monthly)]
        violations = [{"month": month, "abs_difference": str(delta)}
                      for month, delta in differences if delta > tolerance]
        aggregation[field] = {"max_abs_difference": str(max(delta for _, delta in differences)),
                              "absolute_tolerance": str(tolerance), "violations": violations}
        if violations:
            raise ValueError(f"Event-to-monthly aggregation failed: {field}")
    no_events = [month for month in months if counts[month] == 0]
    monthly_by_date = dict(zip(months, monthly))
    for month in no_events:
        if any(Decimal(monthly_by_date[month][field]) != 0 for field in FIELDS.values()):
            raise ValueError(f"Nonzero supplied value without retained events: {month}")
    identities = {}
    for frequency, rows, policy_field in [("event", events, "pc1"), ("monthly", monthly, "pc1_hf")]:
        for decomposition in ["pm", "median"]:
            delta = [abs(Decimal(row[f"MP_{decomposition}"]) + Decimal(row[f"CBI_{decomposition}"])
                         - Decimal(row[policy_field])) for row in rows]
            tolerance = Decimal("1e-8") * (max(counts.values()) if frequency == "monthly" else 1)
            identities[f"{frequency}_{decomposition}"] = {"max_abs_difference": str(max(delta)),
                                                          "absolute_tolerance": str(tolerance)}
            if max(delta) > tolerance:
                raise ValueError(f"Decomposition identity failed: {frequency} {decomposition}")
    poor_man_failures = []
    for row in events:
        p, e = Decimal(row["pc1"]), Decimal(row["STOXX50"])
        expected = (p, Decimal(0)) if p * e < 0 else (Decimal(0), p)
        actual = Decimal(row["MP_pm"]), Decimal(row["CBI_pm"])
        if actual != expected:
            poor_man_failures.append(row["date"])
    if poor_man_failures:
        raise ValueError("Poor-man sign assignment differs from the retained event file")
    inputs = ["OIS_1M", "OIS_3M", "OIS_6M", "OIS_1Y"]
    partial = [{"date": d, "missing_inputs": [name for name in inputs if name not in raw[d]]}
               for d in dates if any(name not in raw[d] for name in inputs)]
    equity_deltas = [abs(Decimal(row["STOXX50"]) - raw[row["date"]]["STOXX50"]) for row in events]
    if max(equity_deltas) > Decimal("1e-12"):
        raise ValueError("Raw-to-derived equity surprise check failed")
    pairs = [("jk_ecb_events.csv", "current_event_shocks"),
             ("jk_ecb_monthly.csv", "current_monthly_shocks")]
    source_comparisons = {}
    for retained, role in pairs:
        source_comparisons[retained] = {"retained_sha256": digest(snapshot / retained),
                                       "upstream_sha256": digest(evidence / sources[role]["file"])}
        source_comparisons[retained]["identical_bytes"] = (
            source_comparisons[retained]["retained_sha256"] == source_comparisons[retained]["upstream_sha256"])
    previous_hash = metadata["recorded_previous_workbook"]["sha256"]
    source_comparisons["ea_mpd_workbook"] = {"recorded_previous_sha256": previous_hash,
                                            "retrieved_sha256": digest(workbook),
                                            "matches_recorded_previous_hash": previous_hash == digest(workbook)}
    report = {
        "purpose": "shock-source reconciliation and numerical construction audit before estimation",
        "retained_snapshot": str(snapshot),
        "source_review_manifest": str(metadata_path),
        "source_review_manifest_sha256": digest(metadata_path),
        "workbook_sha256": digest(workbook),
        "upstream_commit": metadata["upstream_commit"],
        "raw_window_coverage": coverage,
        "derived_event_rows": len(events),
        "derived_monthly_rows": len(monthly),
        "excluded_events": [{"date": d, "reason": exclusions[d],
                             "basis": "Explicit upstream main.m exclusion and exact raw/derived date-set difference"}
                            for d in missing_derived],
        "unexpected_derived_dates": unexpected_derived,
        "source_vintage_comparisons": source_comparisons,
        "monthly_aggregation": aggregation,
        "decomposition_identities": identities,
        "poor_man_sign_assignment_matches": True,
        "raw_equity_max_abs_difference": str(max(equity_deltas)),
        "missing_input_rows_after_exclusions": partial,
        "all_four_ois_inputs_missing": [row["date"] for row in partial if len(row["missing_inputs"]) == 4],
        "missing_equity_dates": [d for d in dates if "STOXX50" not in raw[d]],
        "zero_semantics": {
            "months_without_retained_events": no_events,
            "number_of_months_without_retained_events": len(no_events),
            "number_of_months_with_retained_events": len(counts),
            "event_count_distribution": {str(k): v for k, v in sorted(Counter(counts.values()).items())},
            "recorded_zero_pc1_events": [row["date"] for row in events if Decimal(row["pc1"]) == 0],
            "all_four_observed_ois_inputs_zero_events": [d for d in dates
                                                       if all(raw[d].get(name) == 0 for name in inputs)],
            "event_months_with_exactly_zero_pc1_sum": [month for month in months
                                                      if counts[month] and sums[month]["pc1_hf"] == 0],
            "supplied_monthly_missing_values": 0,
            "outside_source_span": "Missing coverage; no inference that shocks are zero",
            "interpretation": "No-retained-event zeros are exact monthly aggregation conventions, not measured event surprises or complete-calendar claims.",
            "zero_factor_limit": "An event with a zero policy factor can have a nonzero equity surprise and offsetting nonzero median policy and information components.",
        },
        "licence_facts": metadata["licence_facts"],
        "limits": [
            "Exclusion reasons are established here as the author's explicit reasons, not independently verified event-history claims.",
            "The current retrieval is not a real-time historical vintage and does not establish a complete external announcement calendar.",
            "Construction and aggregation agreement do not validate the sign restrictions or causal exogeneity.",
            "No local projections or main outcome estimates have been computed.",
        ],
    }
    if recreate:
        report["independent_numerical_construction"] = construction_check(raw, events)
        if not all(report["independent_numerical_construction"][k] for k in ["pc1_matches", "median_matches"]):
            raise ValueError("Independent PCA or median construction differs from retained shocks")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=ROOT / "data/raw/2026-10-10")
    parser.add_argument("--evidence", type=Path, required=True,
                        help="Directory outside the repository containing the source files recorded in the metadata")
    parser.add_argument("--metadata", type=Path,
                        default=ROOT / "data/metadata/shock_source_review_2026-10-10.json")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/shock_source_reconciliation.json")
    parser.add_argument("--skip-construction", action="store_true")
    args = parser.parse_args()
    report = audit(args.snapshot, args.evidence, args.metadata,
                   recreate=not args.skip_construction)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "derived_events": report["derived_event_rows"],
                      "excluded_dates": [row["date"] for row in report["excluded_events"]],
                      "monthly_aggregation_passed": True,
                      "numerical_construction_checked": not args.skip_construction}, indent=2))


if __name__ == "__main__":
    main()

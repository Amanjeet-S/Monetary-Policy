"""Audit the retained public snapshot. This module does not estimate policy effects."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/raw/2026-10-10"


def months_between(first: str, last: str) -> list[str]:
    start = date.fromisoformat(first + "-01")
    stop = date.fromisoformat(last + "-01")
    indices = range(start.year * 12 + start.month - 1,
                    stop.year * 12 + stop.month)
    return [f"{i // 12:04d}-{i % 12 + 1:02d}" for i in indices]


def read_single_series(path: Path) -> dict[str, float]:
    """Read JSON-stat with exactly one series and a final time dimension."""
    data = json.loads(path.read_text())
    if data["id"][-1] != "time" or any(n != 1 for n in data["size"][:-1]):
        raise ValueError(f"Expected one time series in {path.name}")
    category = data["dimension"]["time"]["category"]["index"]
    times = category if isinstance(category, dict) else dict(zip(category, range(len(category))))
    values = data["value"]
    if isinstance(values, list):
        values = {str(i): v for i, v in enumerate(values)}
    series = {}
    for month, index in times.items():
        value = values.get(str(index))
        if value is None:
            continue
        date.fromisoformat(month + "-01")
        if not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f"Invalid observation at {month} in {path.name}")
        series[month] = float(value)
    if not series:
        raise ValueError(f"No observations in {path.name}")
    return series


def describe_months(months) -> dict:
    ordered = sorted(months)
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("Empty or duplicate monthly keys")
    return {
        "observations": len(ordered), "first": ordered[0], "last": ordered[-1],
        "missing_within_range": sorted(set(months_between(ordered[0], ordered[-1])) - set(ordered)),
    }


def audit(snapshot: Path = SNAPSHOT) -> dict:
    manifest = json.loads((snapshot / "manifest.json").read_text())
    for source in manifest["sources"]:
        actual = hashlib.sha256((snapshot / source["file"]).read_bytes()).hexdigest()
        if actual != source["sha256"]:
            raise ValueError(f"Source hash mismatch: {source['file']}")

    series = {
        "durable_production": read_single_series(snapshot / "eurostat_DE_MIG_DCOG.json"),
        "nondurable_production": read_single_series(snapshot / "eurostat_DE_MIG_NDCOG.json"),
        "hicp": read_single_series(snapshot / "eurostat_hicp_DE.json"),
    }
    report = {name: describe_months(values) for name, values in series.items()}
    with (snapshot / "jk_ecb_monthly.csv").open(newline="") as stream:
        monthly = list(csv.DictReader(stream))
    keys = [f"{int(r['year']):04d}-{int(r['month']):02d}" for r in monthly]
    report["monthly_shocks"] = describe_months(keys)
    for row in monthly:
        for field, value in row.items():
            if value is None or not math.isfinite(float(value)):
                raise ValueError(f"Missing or invalid shock value: {field}")

    with (snapshot / "jk_ecb_events.csv").open(newline="") as stream:
        events = list(csv.DictReader(stream))
    dates = [date.fromisoformat(row["date"]).isoformat() for row in events]
    if not dates or len(set(dates)) != len(dates):
        raise ValueError("Empty or duplicate event dates")
    report["event_shocks"] = {"observations": len(dates), "first": min(dates), "last": max(dates)}
    common = set(keys).intersection(*(set(values) for values in series.values()))
    report["common_months_before_transformations"] = describe_months(common)
    report["interpretation"] = "Coverage only; no causal estimates, imputation or statistical-power claim."
    report["verified_source_files"] = len(manifest["sources"])
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))

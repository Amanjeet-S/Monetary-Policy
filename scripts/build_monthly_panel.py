"""Align retained monthly sources without estimating effects or changing their scale."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path

from audit_germany_data import (
    ROOT,
    SNAPSHOT,
    audit,
    describe_months,
    months_between,
    read_single_series,
)

PANEL_PATH = ROOT / "data/processed/monthly_panel.csv"
REPORT_PATH = ROOT / "reports/panel_build.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_panel() -> dict:
    """Verify source bytes first, then write a calendar-aligned data panel and report."""
    source_audit = audit()
    indices = {
        "durable_index": read_single_series(SNAPSHOT / "eurostat_DE_MIG_DCOG.json"),
        "nondurable_index": read_single_series(SNAPSHOT / "eurostat_DE_MIG_NDCOG.json"),
        "hicp_index": read_single_series(SNAPSHOT / "eurostat_hicp_DE.json"),
    }

    with (SNAPSHOT / "jk_ecb_monthly.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        shock_fields = [field for field in reader.fieldnames or [] if field not in {"year", "month"}]
        if not shock_fields:
            raise ValueError("The retained monthly file has no shock fields")
        monthly_shocks = {
            f"{int(row['year']):04d}-{int(row['month']):02d}": {
                field: row[field] for field in shock_fields
            }
            for row in reader
        }

    with (SNAPSHOT / "jk_ecb_events.csv").open(newline="", encoding="utf-8") as stream:
        event_dates = [date.fromisoformat(row["date"]).isoformat() for row in csv.DictReader(stream)]
    event_counts = Counter(event_date[:7] for event_date in event_dates)
    event_first_month, event_last_month = min(event_counts), max(event_counts)
    event_covered_months = set(months_between(event_first_month, event_last_month))

    observed_months = set(monthly_shocks) | set(event_counts)
    for values in indices.values():
        observed_months.update(values)
    calendar = months_between(min(observed_months), max(observed_months))
    complete_months = []
    rows = []
    for month in calendar:
        row = {"month": month}
        row.update({field: values.get(month, "") for field, values in indices.items()})
        raw_shocks = monthly_shocks.get(month)
        row.update({
            f"shock_{field}": raw_shocks[field] if raw_shocks is not None else ""
            for field in shock_fields
        })
        row["derived_event_count"] = event_counts[month] if month in event_covered_months else ""
        complete = (
            all(month in values for values in indices.values())
            and raw_shocks is not None
            and month in event_covered_months
        )
        row["complete_source_month"] = int(complete)
        if complete:
            complete_months.append(month)
        rows.append(row)

    fieldnames = [
        "month", *indices, *(f"shock_{field}" for field in shock_fields),
        "derived_event_count", "complete_source_month",
    ]
    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PANEL_PATH.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    manifest_path = SNAPSHOT / "manifest.json"
    report = {
        "purpose": "initial_monthly_source_alignment_only",
        "raw_manifest": {
            "path": manifest_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(manifest_path),
        },
        "source_audit": source_audit,
        "panel": {
            "path": PANEL_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256(PANEL_PATH),
            "fields": fieldnames,
            "calendar": describe_months(calendar),
            "complete_source_months": describe_months(complete_months),
            "complete_source_month_definition": (
                "All three index observations and the supplied monthly shock row are present, "
                "and the month lies within the retained derived event file's monthly span. "
                "This flag does not validate identification or the completeness of the ECB event schedule."
            ),
        },
        "derived_event_counts": {
            "source_path": (SNAPSHOT / "jk_ecb_events.csv").relative_to(ROOT).as_posix(),
            "first_date": min(event_dates),
            "last_date": max(event_dates),
            "covered_months": describe_months(event_covered_months),
            "retained_event_rows": len(event_dates),
            "panel_event_count_sum": sum(
                row["derived_event_count"] for row in rows if row["derived_event_count"] != ""
            ),
            "months_with_retained_events": len(event_counts),
            "covered_months_without_retained_events": len(event_covered_months - set(event_counts)),
            "meaning": (
                "Count of rows in the retained derived event file. Zero within its monthly span "
                "means no retained rows for that month; it does not establish that no ECB event "
                "occurred. Counts outside that span are blank. The recorded 315 versus 312 "
                "raw-to-derived event discrepancy remains unresolved."
            ),
        },
        "alignment_conventions": {
            "join": "Outer calendar join from the earliest to latest observed monthly source date",
            "absent_observations": "Empty CSV fields; no imputation",
            "shock_values": "Provider numeric strings retained exactly, including negative zeros",
            "index_values": "Observed index levels read from JSON-stat without rescaling or transformation",
        },
        "interpretation_limits": [
            "No estimation, log transformation, renormalisation or fabricated shocks has been performed.",
            "Complete source coverage does not establish exogeneity, statistical power or a final estimation sample.",
            "Source observations are a retained retrieval of historical values, not an as-published historical vintage.",
            "Event exclusions, identification assumptions, shock choice, transformations, controls and inference remain unresolved.",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = build_panel()
    print(json.dumps({
        "panel": result["panel"],
        "retained_event_rows": result["derived_event_counts"]["retained_event_rows"],
        "report_path": REPORT_PATH.relative_to(ROOT).as_posix(),
    }, indent=2))

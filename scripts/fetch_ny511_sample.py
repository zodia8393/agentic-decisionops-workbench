#!/usr/bin/env python3
"""Fetch a small public NY 511 event sample for the incident decision surface."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_OUTPUT = Path("data/public/ny_511_events_sample.json")
DATASET_ID = "ah74-pg4w"
API_URL = f"https://data.ny.gov/resource/{DATASET_ID}.json"
CATALOG_URL = "https://catalog.data.gov/dataset/511-ny-events-beginning-2010"
EVENT_TYPES = [
    "accident",
    "incident",
    "crash",
    "crash with injuries",
    "crash with property damage",
    "disabled vehicle",
    "disabled tractor trailer",
    "disabled truck",
    "heavy traffic",
    "debris on roadway",
    "debris spill",
    "downed tree",
    "vehicle fire",
    "flooding",
    "police department activity",
    "crash investigation",
]


def build_query(limit: int) -> str:
    event_values = ",".join(f"'{event_type}'" for event_type in EVENT_TYPES)
    params = {
        "$select": (
            "event_type, organization_name, facility_name, direction, city, county, state, "
            "create_time, close_time, event_description, responding_organization_id, "
            "latitude, longitude"
        ),
        "$where": f"event_type in({event_values})",
        "$limit": str(limit),
        "$order": "create_time DESC",
    }
    return API_URL + "?" + urllib.parse.urlencode(params)


def fetch_rows(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=60) as response:
        rows = json.load(response)
    if not isinstance(rows, list):
        raise ValueError("NY 511 API returned a non-list payload")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    url = build_query(args.limit)
    rows = fetch_rows(url)
    if len(rows) < min(args.limit, 50):
        raise SystemExit(f"expected at least {min(args.limit, 50)} rows, got {len(rows)}")

    payload = {
        "domain": "traffic_incident",
        "source_status": "open_data",
        "source_count": 1,
        "source": {
            "name": "511 NY Events: Beginning 2010",
            "publisher": "data.ny.gov / New York State",
            "dataset_id": DATASET_ID,
            "catalog_url": CATALOG_URL,
            "api_url": API_URL,
            "query_url": url,
            "access_level": "public",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "notes": (
                "Small reproducible sample of public NY 511 event records; "
                "no raw CCTV, video, private logs, or credentials."
            ),
        },
        "events": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()

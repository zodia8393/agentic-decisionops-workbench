"""Public-safe adapter over the bike-share operations ML artifacts."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BIKE_SHARE_ROOT = Path(
    "/DATA/HJ/prj/data-scientist-career/projects/bike-share-demand-resilience"
)


@dataclass(frozen=True)
class BikeShareArtifacts:
    """Small public-safe view of the upstream bike-share decision surface."""

    stations: list[dict[str, Any]]
    readiness: dict[str, Any]
    deployment: dict[str, Any]
    model_summary: dict[str, Any]
    quality_gates: list[dict[str, Any]]
    source_status: str


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _public_station(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "station_short_name": row.get("station_short_name", ""),
        "station_name": row.get("station_name", ""),
        "forecast_24h": round(_to_float(row.get("forecast_24h")), 3),
        "upper_demand_24h": round(_to_float(row.get("upper_demand_24h")), 3),
        "capacity": round(_to_float(row.get("capacity")), 3),
        "risk_score": round(_to_float(row.get("risk_score")), 3),
        "recommended_buffer_bikes": round(_to_float(row.get("recommended_buffer_bikes")), 3),
        "num_bikes_available": round(_to_float(row.get("num_bikes_available")), 3),
        "current_bike_shortage": _to_bool(row.get("current_bike_shortage")),
        "current_dock_shortage": _to_bool(row.get("current_dock_shortage")),
        "inventory_pressure": round(_to_float(row.get("inventory_pressure")), 3),
        "live_shortage_boost": round(_to_float(row.get("live_shortage_boost")), 3),
    }


def _fallback_artifacts() -> BikeShareArtifacts:
    stations = [
        {
            "station_short_name": "DEMO01",
            "station_name": "Demo Terminal",
            "forecast_24h": 58.0,
            "upper_demand_24h": 71.0,
            "capacity": 12.0,
            "risk_score": 6.7,
            "recommended_buffer_bikes": 15.0,
            "num_bikes_available": 1.0,
            "current_bike_shortage": True,
            "current_dock_shortage": False,
            "inventory_pressure": 0.92,
            "live_shortage_boost": 0.75,
        },
        {
            "station_short_name": "DEMO02",
            "station_name": "Demo Park",
            "forecast_24h": 34.0,
            "upper_demand_24h": 43.0,
            "capacity": 20.0,
            "risk_score": 2.1,
            "recommended_buffer_bikes": 6.0,
            "num_bikes_available": 11.0,
            "current_bike_shortage": False,
            "current_dock_shortage": False,
            "inventory_pressure": 0.25,
            "live_shortage_boost": 0.0,
        },
    ]
    return BikeShareArtifacts(
        stations=stations,
        readiness={
            "ready_for_prospective_validation": False,
            "decision": "NOT_READY",
            "snapshot_count": 0,
            "target_snapshots": 336,
            "coverage_ratio": 0.0,
            "reason": "demo fallback without live snapshot history",
        },
        deployment={"decision": "NO_GO", "blockers": ["demo fallback data"]},
        model_summary={
            "best_model": "demo_gradient_boosting",
            "best_test_mae": 1.0,
            "baseline_test_mae": 1.2,
            "conformal_test_coverage": 0.89,
        },
        quality_gates=[
            {"gate": "demo decision output", "passed": True, "evidence": "fallback fixture"}
        ],
        source_status="fallback",
    )


class BikeShareArtifactAdapter:
    """Loads derived public-safe artifacts from the upstream bike-share project."""

    def __init__(self, root: Path | str = DEFAULT_BIKE_SHARE_ROOT) -> None:
        self.root = Path(root)

    def load(self) -> BikeShareArtifacts:
        station_reports = self.root / "station_level" / "reports"
        station_data = self.root / "station_level" / "data" / "processed"
        priority_rows = _read_csv(station_reports / "station_rebalancing_priority.csv", limit=12)
        if not priority_rows:
            return _fallback_artifacts()

        readiness = _read_json(station_reports / "station_snapshot_readiness.json")
        deployment = _read_json(station_reports / "station_public_deploy_readiness.json")
        run_summary = _read_json(station_reports / "station_run_summary.json")
        inventory_summary = _read_json(station_reports / "latest_inventory_snapshot_summary.json")
        quality_rows = _read_csv(station_reports / "station_quality_gate_checks.csv")
        stations = [_public_station(row) for row in priority_rows]

        readiness_view = {
            "ready_for_prospective_validation": bool(
                readiness.get("ready_for_prospective_validation", False)
            ),
            "decision": "READY" if readiness.get("ready_for_prospective_validation") else "NOT_READY",
            "snapshot_count": readiness.get("snapshot_count", 0),
            "target_snapshots": readiness.get("target_snapshots", 336),
            "coverage_ratio": round(_to_float(readiness.get("coverage_ratio")), 3),
            "reason": readiness.get("reason", "unknown"),
            "earliest_ready_at": readiness.get("earliest_ready_at"),
        }
        deployment_view = {
            "decision": deployment.get("decision", "NO_GO"),
            "blockers": deployment.get("blockers", []),
            "snapshot_ready": deployment.get("service_health", {}).get("snapshot_ready", False),
        }
        model_summary = {
            "best_model": run_summary.get("best_model", "unknown"),
            "best_test_mae": run_summary.get("best_test_mae"),
            "baseline_test_mae": run_summary.get("baseline_test_mae"),
            "conformal_test_coverage": run_summary.get("conformal_summary", {}).get(
                "conformal_test_coverage"
            ),
            "inventory_rows": inventory_summary.get("inventory", {}).get("inventory_rows"),
            "bike_shortage_rows": inventory_summary.get("inventory", {}).get("bike_shortage_rows"),
            "dock_shortage_rows": inventory_summary.get("inventory", {}).get("dock_shortage_rows"),
        }
        return BikeShareArtifacts(
            stations=stations,
            readiness=readiness_view,
            deployment=deployment_view,
            model_summary=model_summary,
            quality_gates=quality_rows,
            source_status="loaded",
        )

    def write_public_fixture(self, output_root: Path) -> Path:
        artifacts = self.load()
        data_dir = output_root / "data" / "processed"
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "bike_share_decision_surface.json"
        payload = {
            "domain": "bike_share",
            "source_status": artifacts.source_status,
            "stations": artifacts.stations,
            "readiness": artifacts.readiness,
            "deployment": artifacts.deployment,
            "model_summary": artifacts.model_summary,
            "quality_gates": artifacts.quality_gates,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

"""Public/open traffic incident adapter for cross-domain DecisionOps tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OPEN_DATA_FIXTURE = (
    Path(__file__).resolve().parents[3] / "data" / "public" / "ny_511_events_sample.json"
)


@dataclass(frozen=True)
class TrafficIncidentArtifacts:
    """Public/open traffic incident decision surface."""

    incidents: list[dict[str, Any]]
    readiness: dict[str, Any]
    deployment: dict[str, Any]
    source_status: str
    source_count: int
    source_metadata: dict[str, Any] | None = None


def _fallback_incidents() -> list[dict[str, Any]]:
    return [
        {
            "incident_id": "INC-001",
            "corridor": "urban-arterial-west",
            "event_type": "lane_blocking_vehicle",
            "severity_score": 8.4,
            "evidence_age_minutes": 18,
            "sensor_conflict_rate": 0.12,
            "public_release_allowed": False,
            "recommended_action": "operator_review_before_dispatch",
            "evidence_sources": ["cctv_event_counter", "operator_log", "weather_alert"],
        },
        {
            "incident_id": "INC-002",
            "corridor": "river-bridge-eastbound",
            "event_type": "slowdown_cluster",
            "severity_score": 6.2,
            "evidence_age_minutes": 42,
            "sensor_conflict_rate": 0.24,
            "public_release_allowed": True,
            "recommended_action": "publish_advisory_after_review",
            "evidence_sources": ["speed_probe", "operator_log", "public_event_calendar"],
        },
        {
            "incident_id": "INC-003",
            "corridor": "industrial-ring-road",
            "event_type": "stale_detection",
            "severity_score": 7.1,
            "evidence_age_minutes": 96,
            "sensor_conflict_rate": 0.36,
            "public_release_allowed": False,
            "recommended_action": "refresh_evidence_and_review",
            "evidence_sources": ["cctv_event_counter", "speed_probe", "weather_alert"],
        },
    ]


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_minutes(start: Any, end: Any) -> float:
    started = _parse_time(start)
    ended = _parse_time(end)
    if not started or not ended:
        return 999.0
    return max(0.0, (ended - started).total_seconds() / 60.0)


def _severity_score(event: dict[str, Any], duration_minutes: float) -> float:
    event_type = str(event.get("event_type", "")).lower()
    base = 5.8
    if "injur" in event_type:
        base = 9.2
    elif "vehicle fire" in event_type:
        base = 8.7
    elif "crash" in event_type or "accident" in event_type:
        base = 8.1
    elif "flood" in event_type or "downed tree" in event_type:
        base = 7.6
    elif "police" in event_type or event_type == "incident":
        base = 7.2
    elif "debris" in event_type:
        base = 6.9
    elif "disabled" in event_type:
        base = 6.4
    elif "heavy traffic" in event_type:
        base = 6.2
    if duration_minutes >= 180:
        base += 0.8
    elif duration_minutes >= 60:
        base += 0.4
    return round(min(base, 9.9), 2)


def _source_conflict_rate(event: dict[str, Any], duration_minutes: float) -> float:
    event_type = str(event.get("event_type", "")).lower()
    generic_event = event_type in {"incident", "police department activity"}
    missing_description = not str(event.get("event_description", "")).strip()
    long_running = duration_minutes >= 180
    score = 0.08
    if generic_event:
        score += 0.12
    if missing_description:
        score += 0.08
    if long_running:
        score += 0.1
    return round(min(score, 0.42), 2)


def _event_to_incident(event: dict[str, Any], index: int) -> dict[str, Any]:
    duration = _duration_minutes(event.get("create_time"), event.get("close_time"))
    severity = _severity_score(event, duration)
    conflict = _source_conflict_rate(event, duration)
    event_type = str(event.get("event_type", "unknown")).lower()
    facility = event.get("facility_name") or "unknown facility"
    direction = event.get("direction") or "unknown direction"
    county = event.get("county") or "unknown county"
    public_release_allowed = severity < 7.0 and conflict < 0.2
    return {
        "incident_id": f"NY511-{index + 1:04d}",
        "source_event_type": event_type,
        "corridor": f"{facility} {direction} ({county})",
        "event_type": event_type.replace(" ", "_"),
        "severity_score": severity,
        "evidence_age_minutes": round(duration, 1),
        "sensor_conflict_rate": conflict,
        "public_release_allowed": public_release_allowed,
        "source_public": True,
        "recommended_action": (
            "operator_review_before_publication"
            if not public_release_allowed
            else "publish_advisory_after_review"
        ),
        "evidence_sources": [
            "ny_511_event_record",
            "ny_511_responder",
            "ny_511_georeference",
        ],
        "raw_event": {
            "event_type": event.get("event_type"),
            "organization_name": event.get("organization_name"),
            "facility_name": event.get("facility_name"),
            "direction": event.get("direction"),
            "city": event.get("city"),
            "county": event.get("county"),
            "create_time": event.get("create_time"),
            "close_time": event.get("close_time"),
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
        },
    }


def _open_data_artifacts(payload: dict[str, Any]) -> TrafficIncidentArtifacts:
    events = list(payload.get("events", []))
    incidents = [_event_to_incident(event, idx) for idx, event in enumerate(events)]
    source = dict(payload.get("source", {}))
    event_types = sorted({str(row.get("event_type", "unknown")).lower() for row in events})
    create_times = [str(row.get("create_time", "")) for row in events if row.get("create_time")]
    return TrafficIncidentArtifacts(
        incidents=incidents,
        readiness={
            "decision": "HUMAN_REVIEW_REQUIRED",
            "ready_for_autonomous_action": False,
            "source_count": int(payload.get("source_count", 1) or 1),
            "record_count": len(events),
            "event_types": event_types,
            "earliest_event_time": min(create_times) if create_times else None,
            "latest_event_time": max(create_times) if create_times else None,
            "reason": "public NY 511 event records support review workflows, not autonomous dispatch or publication",
        },
        deployment={
            "decision": "REVIEW_REQUIRED",
            "blockers": [
                "incident advisories require operator confirmation before publication",
                "historical open-data records are not a live dispatch authority",
            ],
        },
        source_status=str(payload.get("source_status", "open_data")),
        source_count=int(payload.get("source_count", 1) or 1),
        source_metadata=source,
    )


class TrafficIncidentAdapter:
    """Provides a second domain without exposing raw CCTV frames or private logs."""

    def __init__(self, fixture_path: Path | str | None = None) -> None:
        self.fixture_path = Path(fixture_path) if fixture_path else None

    def load(self) -> TrafficIncidentArtifacts:
        fixture_path = self.fixture_path or DEFAULT_OPEN_DATA_FIXTURE
        if fixture_path.is_file():
            payload = json.loads(fixture_path.read_text(encoding="utf-8"))
            if "events" in payload:
                return _open_data_artifacts(payload)
            return TrafficIncidentArtifacts(
                incidents=list(payload.get("incidents", [])),
                readiness=dict(payload.get("readiness", {})),
                deployment=dict(payload.get("deployment", {})),
                source_status="loaded",
                source_count=int(payload.get("source_count", 0) or 0),
                source_metadata=dict(payload.get("source", {})),
            )
        incidents = _fallback_incidents()
        return TrafficIncidentArtifacts(
            incidents=incidents,
            readiness={
                "decision": "HUMAN_REVIEW_REQUIRED",
                "ready_for_autonomous_action": False,
                "source_count": 3,
                "holdout_tasks": 18,
                "reason": "camera-derived or conflicting evidence requires reviewer approval",
            },
            deployment={
                "decision": "NO_GO",
                "blockers": [
                    "raw CCTV frames are not publishable",
                    "high-severity incidents require human confirmation",
                ],
            },
            source_status="fallback",
            source_count=3,
        )

    def write_public_fixture(self, output_root: Path) -> Path:
        artifacts = self.load()
        data_dir = output_root / "data" / "processed"
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "traffic_incident_decision_surface.json"
        payload = {
            "domain": "traffic_incident",
            "source_status": artifacts.source_status,
            "source_count": artifacts.source_count,
            "source": artifacts.source_metadata or {},
            "incidents": artifacts.incidents,
            "readiness": artifacts.readiness,
            "deployment": artifacts.deployment,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

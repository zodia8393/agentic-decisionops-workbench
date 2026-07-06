"""Public-safe adapter over Control Tower Seoul impact-card artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONTROL_TOWER_ROOT = Path(
    "/DATA/HJ/prj/data-scientist-career/projects/decisionops-control-tower"
)


@dataclass(frozen=True)
class SeoulImpactArtifacts:
    """Reviewer-safe Seoul Ddareungi impact decision surface."""

    cards: list[dict[str, Any]]
    summary: dict[str, Any]
    source_status: str
    source_count: int


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _public_card(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "impact_card_id": row.get("impact_card_id", ""),
        "domain": row.get("domain", "seoul_ddareungi"),
        "priority": row.get("priority", ""),
        "station_id": row.get("station_id", ""),
        "station_name": row.get("station_name", ""),
        "issue_type": row.get("issue_type", ""),
        "recommended_action": row.get("recommended_action", ""),
        "recommended_bikes_delta": _to_int(row.get("recommended_bikes_delta")),
        "candidate_units_addressed": _to_int(row.get("candidate_units_addressed")),
        "expected_delta_vs_no_action_units": _to_int(
            row.get("expected_delta_vs_no_action_units")
        ),
        "verified_delta_vs_no_action_units": row.get("verified_delta_vs_no_action_units", ""),
        "impact_metric": row.get("impact_metric", ""),
        "impact_rationale": row.get("impact_rationale", ""),
        "severity_score": round(_to_float(row.get("severity_score")), 3),
        "validation_status": row.get("validation_status", "NOT_READY"),
        "evidence_strength": row.get("evidence_strength", "preliminary"),
        "confidence_score": round(_to_float(row.get("confidence_score")), 3),
        "guardrail_state": row.get("guardrail_state", "validation_not_ready"),
        "public_claim_state": row.get(
            "public_claim_state", "blocked_until_validation_ready"
        ),
        "blocker": row.get("blocker", ""),
        "evidence": row.get("evidence", ""),
        "captured_at_kst": row.get("captured_at_kst", ""),
        "coordinate_status": row.get("coordinate_status", ""),
    }


def _fallback_artifacts() -> SeoulImpactArtifacts:
    cards = [
        {
            "impact_card_id": "SEOUL-IMPACT-DEMO-001",
            "domain": "seoul_ddareungi",
            "priority": "P1",
            "station_id": "DEMO-SEOUL-01",
            "station_name": "Demo Ddareungi Station",
            "issue_type": "bike_shortage",
            "recommended_action": "add_bikes",
            "recommended_bikes_delta": 6,
            "candidate_units_addressed": 6,
            "expected_delta_vs_no_action_units": 6,
            "verified_delta_vs_no_action_units": "",
            "impact_metric": "rental_shortage_pressure_units",
            "impact_rationale": "Demo impact card for regression tests.",
            "severity_score": 1.4,
            "validation_status": "NOT_READY",
            "evidence_strength": "preliminary",
            "confidence_score": 0.5,
            "guardrail_state": "validation_not_ready",
            "public_claim_state": "blocked_until_validation_ready",
            "blocker": "demo fallback without Seoul validation snapshots",
            "evidence": "demo/seoul_impact_cards.json",
            "captured_at_kst": "",
            "coordinate_status": "demo",
        }
    ]
    return SeoulImpactArtifacts(
        cards=cards,
        summary={
            "impact_card_rows": len(cards),
            "impact_candidate_units_addressed": 6,
            "seoul_validation_status": "NOT_READY",
            "seoul_model_status": "NOT_READY",
            "public_claim_state": "blocked_until_validation_ready",
        },
        source_status="fallback",
        source_count=1,
    )


class SeoulImpactAdapter:
    """Loads Control Tower impact cards without exposing raw station feeds."""

    def __init__(self, root: Path | str = DEFAULT_CONTROL_TOWER_ROOT) -> None:
        self.root = Path(root)

    def load(self) -> SeoulImpactArtifacts:
        reports = self.root / "reports"
        raw_cards = _read_json(reports / "impact_cards.json", [])
        if not raw_cards:
            return _fallback_artifacts()
        cards = [_public_card(row) for row in raw_cards]
        control_state = _read_json(reports / "control_state.json", {})
        metrics = dict(control_state.get("metrics", {}))
        source_status = dict(control_state.get("source_status", {}))
        public_claim_states = [
            str(row.get("public_claim_state", "")).lower() for row in cards
        ]
        blocked_claim_states = [
            state for state in public_claim_states if state.startswith("blocked")
        ]
        if blocked_claim_states:
            public_claim_state = (
                blocked_claim_states[0]
                if len(set(blocked_claim_states)) == 1
                else "blocked_mixed_public_claim_states"
            )
        elif all(row.get("guardrail_state") == "ready_for_review" for row in cards):
            public_claim_state = "ready_for_claim"
        else:
            public_claim_state = "blocked_until_validation_ready"
        summary = {
            "impact_card_rows": len(cards),
            "impact_candidate_units_addressed": sum(
                _to_int(row.get("candidate_units_addressed")) for row in cards
            ),
            "seoul_validation_status": source_status.get(
                "seoul_validation_status", cards[0].get("validation_status", "UNKNOWN")
            ),
            "seoul_model_status": source_status.get("seoul_model_status", "UNKNOWN"),
            "seoul_snapshot_count": metrics.get("seoul_snapshot_count", 0),
            "public_claim_state": public_claim_state,
            "public_claim_blocked_cards": len(blocked_claim_states),
        }
        return SeoulImpactArtifacts(
            cards=cards,
            summary=summary,
            source_status="loaded",
            source_count=1,
        )

    def write_public_fixture(self, output_root: Path) -> Path:
        artifacts = self.load()
        data_dir = output_root / "data" / "processed"
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "seoul_impact_decision_surface.json"
        payload = {
            "domain": "seoul_ddareungi_impact",
            "source_status": artifacts.source_status,
            "source_count": artifacts.source_count,
            "summary": artifacts.summary,
            "impact_cards": artifacts.cards,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

"""Read-only DecisionOps tools over public-safe decision artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_adapters.bike_share import BikeShareArtifacts
from .domain_adapters.seoul_impact import SeoulImpactArtifacts
from .domain_adapters.traffic_incident import TrafficIncidentArtifacts


@dataclass
class ToolResult:
    name: str
    payload: dict[str, Any]
    evidence_id: str


class DecisionTools:
    """Small read-only tool surface used by the agents and eval harness."""

    def __init__(
        self,
        artifacts: BikeShareArtifacts,
        incident_artifacts: TrafficIncidentArtifacts | None = None,
        impact_artifacts: SeoulImpactArtifacts | None = None,
    ) -> None:
        self.artifacts = artifacts
        self.incident_artifacts = incident_artifacts
        self.impact_artifacts = impact_artifacts

    def top_station_risks(self, limit: int = 5) -> ToolResult:
        stations = sorted(
            self.artifacts.stations,
            key=lambda row: float(row.get("risk_score", 0.0)),
            reverse=True,
        )[:limit]
        return ToolResult(
            name="top_station_risks",
            payload={"stations": stations, "limit": limit},
            evidence_id="station_rebalancing_priority",
        )

    def station_evidence(self, station_short_name: str | None = None) -> ToolResult:
        stations = self.artifacts.stations
        station = stations[0] if stations else {}
        if station_short_name:
            station = next(
                (row for row in stations if row.get("station_short_name") == station_short_name),
                station,
            )
        return ToolResult(
            name="station_evidence",
            payload={"station": station},
            evidence_id=f"station:{station.get('station_short_name', 'unknown')}",
        )

    def readiness_status(self) -> ToolResult:
        return ToolResult(
            name="readiness_status",
            payload={
                "readiness": self.artifacts.readiness,
                "deployment": self.artifacts.deployment,
                "model_summary": self.artifacts.model_summary,
            },
            evidence_id="readiness_and_deploy_gate",
        )

    def operator_summary(self) -> ToolResult:
        readiness = self.artifacts.readiness
        deployment = self.artifacts.deployment
        top = self.top_station_risks(limit=3).payload["stations"]
        incident_top = self.top_incident_risks(limit=1).payload["incidents"]
        impact_top = self.top_impact_cards(limit=1).payload["impact_cards"]
        summary = (
            f"snapshot={readiness.get('snapshot_count')}/{readiness.get('target_snapshots')}, "
            f"deploy={deployment.get('decision')}, "
            f"top_station={top[0]['station_short_name'] if top else 'n/a'}, "
            f"top_incident={incident_top[0]['incident_id'] if incident_top else 'n/a'}, "
            f"top_impact={impact_top[0]['impact_card_id'] if impact_top else 'n/a'}"
        )
        return ToolResult(
            name="operator_summary",
            payload={"summary": summary},
            evidence_id="operator_summary",
        )

    def top_incident_risks(self, limit: int = 5) -> ToolResult:
        incidents = []
        if self.incident_artifacts:
            incidents = sorted(
                self.incident_artifacts.incidents,
                key=lambda row: float(row.get("severity_score", 0.0)),
                reverse=True,
            )[:limit]
        return ToolResult(
            name="top_incident_risks",
            payload={"incidents": incidents, "limit": limit},
            evidence_id="traffic_incident_priority",
        )

    def incident_evidence(self, incident_id: str | None = None) -> ToolResult:
        incidents = self.incident_artifacts.incidents if self.incident_artifacts else []
        incident = incidents[0] if incidents else {}
        if incident_id:
            incident = next(
                (row for row in incidents if row.get("incident_id") == incident_id),
                incident,
            )
        return ToolResult(
            name="incident_evidence",
            payload={"incident": incident},
            evidence_id=f"incident:{incident.get('incident_id', 'unknown')}",
        )

    def incident_readiness(self) -> ToolResult:
        readiness = self.incident_artifacts.readiness if self.incident_artifacts else {}
        deployment = self.incident_artifacts.deployment if self.incident_artifacts else {}
        return ToolResult(
            name="incident_readiness",
            payload={
                "incident_readiness": readiness,
                "incident_deployment": deployment,
            },
            evidence_id="traffic_incident_readiness",
        )

    def review_queue_candidates(self) -> ToolResult:
        station = self.station_evidence().payload["station"]
        incident = self.incident_evidence().payload["incident"]
        impact = self.impact_evidence().payload["impact_card"]
        candidates = [
            {
                "domain": "bike_share",
                "subject_id": station.get("station_short_name", "unknown"),
                "priority_reason": "high station risk or deploy readiness blocker",
                "evidence_id": f"station:{station.get('station_short_name', 'unknown')}",
            },
            {
                "domain": "traffic_incident",
                "subject_id": incident.get("incident_id", "unknown"),
                "priority_reason": "camera-derived or conflicting incident evidence",
                "evidence_id": f"incident:{incident.get('incident_id', 'unknown')}",
            },
            {
                "domain": "seoul_ddareungi_impact",
                "subject_id": impact.get("impact_card_id", "unknown"),
                "priority_reason": "impact card has validation, confidence, or public-claim blocker",
                "evidence_id": f"impact:{impact.get('impact_card_id', 'unknown')}",
            },
        ]
        return ToolResult(
            name="review_queue_candidates",
            payload={"review_queue_candidates": candidates},
            evidence_id="human_review_queue_candidates",
        )

    def top_impact_cards(self, limit: int = 5) -> ToolResult:
        cards = self.impact_artifacts.cards if self.impact_artifacts else []

        def sort_key(row: dict[str, Any]) -> tuple[int, float]:
            priority_rank = {"P0": 3, "P1": 2, "P2": 1}.get(str(row.get("priority")), 0)
            try:
                units = float(row.get("candidate_units_addressed", 0.0) or 0.0)
            except (TypeError, ValueError):
                units = 0.0
            return priority_rank, units

        selected = sorted(cards, key=sort_key, reverse=True)[:limit]
        summary = self.impact_artifacts.summary if self.impact_artifacts else {}
        return ToolResult(
            name="top_impact_cards",
            payload={"impact_cards": selected, "impact_summary": summary, "limit": limit},
            evidence_id="seoul_impact_cards",
        )

    def impact_evidence(self, impact_card_id: str | None = None) -> ToolResult:
        cards = self.impact_artifacts.cards if self.impact_artifacts else []
        card = cards[0] if cards else {}
        if impact_card_id:
            card = next(
                (row for row in cards if row.get("impact_card_id") == impact_card_id),
                card,
            )
        return ToolResult(
            name="impact_evidence",
            payload={"impact_card": card},
            evidence_id=f"impact:{card.get('impact_card_id', 'unknown')}",
        )

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        if name == "top_station_risks":
            return self.top_station_risks(limit=int(kwargs.get("limit", 5)))
        if name == "station_evidence":
            return self.station_evidence(kwargs.get("station_short_name"))
        if name == "readiness_status":
            return self.readiness_status()
        if name == "operator_summary":
            return self.operator_summary()
        if name == "top_incident_risks":
            return self.top_incident_risks(limit=int(kwargs.get("limit", 5)))
        if name == "incident_evidence":
            return self.incident_evidence(kwargs.get("incident_id"))
        if name == "incident_readiness":
            return self.incident_readiness()
        if name == "review_queue_candidates":
            return self.review_queue_candidates()
        if name == "top_impact_cards":
            return self.top_impact_cards(limit=int(kwargs.get("limit", 5)))
        if name == "impact_evidence":
            return self.impact_evidence(kwargs.get("impact_card_id"))
        raise ValueError(f"unknown tool: {name}")

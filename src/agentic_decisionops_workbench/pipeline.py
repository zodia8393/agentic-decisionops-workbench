"""CLI pipeline for the Agentic DecisionOps Workbench seed."""

from __future__ import annotations

import argparse
from pathlib import Path

from .evals import run_evaluation
from .mcp_contract import write_contract
from .planner_replay import DEFAULT_PLANNER_REPLAY_PATH
from .reports import write_quality_scores, write_reports


DEFAULT_OUTPUT_ROOT = Path(
    "/DATA/HJ/prj/data-scientist-career/projects/agentic-decisionops-workbench"
)
DEFAULT_BIKE_SHARE_ROOT = Path(
    "/DATA/HJ/prj/data-scientist-career/projects/bike-share-demand-resilience"
)
DEFAULT_CONTROL_TOWER_ROOT = Path(
    "/DATA/HJ/prj/data-scientist-career/projects/decisionops-control-tower"
)


def run_all(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    bike_share_root: Path = DEFAULT_BIKE_SHARE_ROOT,
    control_tower_root: Path = DEFAULT_CONTROL_TOWER_ROOT,
    planner_replay_path: Path = DEFAULT_PLANNER_REPLAY_PATH,
) -> dict:
    summary = run_evaluation(
        output_root=output_root,
        bike_share_root=bike_share_root,
        control_tower_root=control_tower_root,
        planner_replay_path=planner_replay_path,
    )
    contract_json, contract_md = write_contract(output_root)
    report_paths = write_reports(output_root)
    quality_path = write_quality_scores(output_root, summary)
    summary.update(
        {
            "mcp_contract_json": str(contract_json),
            "mcp_contract_md": str(contract_md),
            "reports": {key: str(path) for key, path in report_paths.items()},
            "quality_scores": str(quality_path),
        }
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="eval", choices=["eval", "run-all"])
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--bike-share-root", default=str(DEFAULT_BIKE_SHARE_ROOT))
    parser.add_argument("--control-tower-root", default=str(DEFAULT_CONTROL_TOWER_ROOT))
    parser.add_argument("--planner-replay-path", default=str(DEFAULT_PLANNER_REPLAY_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_all(
        Path(args.output_root),
        Path(args.bike_share_root),
        Path(args.control_tower_root),
        Path(args.planner_replay_path),
    )
    print(
        "decisionops hardening complete: "
        f"guarded_success_lift={summary['guarded_success_lift']:.3f}, "
        f"reports={summary['reports']['trace_report']}"
    )


if __name__ == "__main__":
    main()

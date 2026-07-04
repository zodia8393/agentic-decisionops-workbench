"""CLI pipeline for the Agentic DecisionOps Workbench seed."""

from __future__ import annotations

import argparse
from pathlib import Path

from .evals import run_evaluation
from .mcp_contract import write_contract
from .reports import write_quality_scores, write_reports


DEFAULT_OUTPUT_ROOT = Path(
    "/DATA/HJ/prj/data-scientist-career/projects/agentic-decisionops-workbench"
)
DEFAULT_BIKE_SHARE_ROOT = Path(
    "/DATA/HJ/prj/data-scientist-career/projects/bike-share-demand-resilience"
)


def run_all(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    bike_share_root: Path = DEFAULT_BIKE_SHARE_ROOT,
) -> dict:
    summary = run_evaluation(output_root=output_root, bike_share_root=bike_share_root)
    contract_json, contract_md = write_contract(output_root)
    report_paths = write_reports(output_root)
    quality_path = write_quality_scores(output_root)
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_all(Path(args.output_root), Path(args.bike_share_root))
    print(
        "decisionops hardening complete: "
        f"guarded_success_lift={summary['guarded_success_lift']:.3f}, "
        f"reports={summary['reports']['trace_report']}"
    )


if __name__ == "__main__":
    main()

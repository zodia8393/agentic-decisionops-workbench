from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentic_decisionops_workbench.pipeline import run_all


def test_pipeline_smoke_writes_decisionops_artifacts(tmp_path):
    summary = run_all(output_root=tmp_path, bike_share_root=tmp_path / "missing")

    assert summary["status"] == "hardened_eval_complete"
    assert summary["guarded_success_lift"] > 0
    assert Path(summary["reports"]["final_report"]).exists()
    assert Path(summary["reports"]["trace_report"]).exists()
    assert (tmp_path / "reports" / "mcp_contract.json").exists()
    assert (tmp_path / "reports" / "failure_taxonomy.csv").exists()

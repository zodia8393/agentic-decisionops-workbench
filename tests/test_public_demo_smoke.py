from email.message import Message
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from smoke_public_demo import PublicDemoSmokeError, fetch_public_demo, validate_demo_html


class FakeResponse:
    def __init__(self, html: str, *, status: int = 200, content_type: str = "text/html"):
        self._html = html.encode("utf-8")
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self) -> str:
        return "https://example.test/demo/"

    def read(self) -> bytes:
        return self._html


def test_repository_demo_satisfies_public_contract():
    html = (ROOT / "docs" / "demo" / "index.html").read_text(encoding="utf-8")

    result = validate_demo_html(html)

    assert result == {"required_marker_count": 3, "missing_markers": []}


def test_public_demo_smoke_rejects_missing_recorded_marker():
    with pytest.raises(PublicDemoSmokeError, match="markers are missing"):
        validate_demo_html("<html><body>unrelated page</body></html>")


def test_public_demo_smoke_rejects_non_html_response():
    html = (ROOT / "docs" / "demo" / "index.html").read_text(encoding="utf-8")

    with pytest.raises(PublicDemoSmokeError, match="unexpected content type"):
        fetch_public_demo(
            "https://example.test/demo/",
            opener=lambda *_args, **_kwargs: FakeResponse(
                html,
                content_type="application/octet-stream",
            ),
        )

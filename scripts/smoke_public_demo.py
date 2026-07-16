#!/usr/bin/env python3
"""Verify that the public recorded demo is reachable and recognizable."""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable
from urllib.request import Request, urlopen


DEFAULT_URL = "https://zodia8393.github.io/agentic-decisionops-workbench/"
REQUIRED_MARKERS = (
    "GitHub Pages · recorded replay",
    'id="demo-cases"',
    "public-safe recorded replay",
)


class PublicDemoSmokeError(RuntimeError):
    """Raised when the deployed demo does not satisfy its public contract."""


def validate_demo_html(html: str) -> dict[str, Any]:
    missing = [marker for marker in REQUIRED_MARKERS if marker not in html]
    if missing:
        raise PublicDemoSmokeError(f"public demo markers are missing: {missing}")
    return {"required_marker_count": len(REQUIRED_MARKERS), "missing_markers": []}


def fetch_public_demo(
    url: str,
    *,
    timeout: float = 10.0,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "decisionops-pages-smoke/1.0"})
    with opener(request, timeout=timeout) as response:
        status = int(response.status)
        content_type = response.headers.get_content_type()
        final_url = response.geturl()
        html = response.read().decode("utf-8")

    if status != 200:
        raise PublicDemoSmokeError(f"public demo returned HTTP {status}")
    if content_type != "text/html":
        raise PublicDemoSmokeError(f"public demo returned unexpected content type: {content_type}")

    contract = validate_demo_html(html)
    return {
        "status": "ok",
        "http_status": status,
        "content_type": content_type,
        "final_url": final_url,
        **contract,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(fetch_public_demo(args.url, timeout=args.timeout), ensure_ascii=False))


if __name__ == "__main__":
    main()

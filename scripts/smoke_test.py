import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import server


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def assert_true(condition, label):
    if not condition:
        raise AssertionError(f"{label}: condition not met")


def run_backend_smoke_tests():
    app = server.app
    client = app.test_client()

    resp = client.post("/api/parse")
    assert_equal(resp.status_code, 400, "missing json status")
    assert_equal(resp.get_json().get("error"), "URL is required", "missing json error")

    resp = client.post("/api/parse", json={"url": "https://x.com/OpenAI/status/123"})
    assert_equal(resp.status_code, 400, "missing platform status")
    assert_equal(resp.get_json().get("error"), "Platform is required", "missing platform error")

    resp = client.post(
        "/api/parse",
        json={"url": "https://example.com", "platform": "Foo"},
    )
    assert_equal(resp.status_code, 400, "unsupported platform status")
    assert_equal(resp.get_json().get("error"), "Unsupported platform", "unsupported platform error")

    resp = client.post(
        "/api/parse",
        json={"url": "https://www.youtube.com/watch?v=short", "platform": "YouTube"},
    )
    assert_equal(resp.status_code, 400, "invalid youtube status")
    assert_equal(resp.get_json().get("error"), "Invalid YouTube URL", "invalid youtube error")

    resp = client.post(
        "/api/parse",
        json={"url": "https://x.com/OpenAI/status/1234567890", "platform": "Twitter"},
    )
    assert_equal(resp.status_code, 200, "twitter status")
    assert_true("title" in resp.get_json(), "twitter title exists")

    return "backend ok"


def run_frontend_smoke_tests():
    html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    js = (REPO_ROOT / "script.js").read_text(encoding="utf-8")

    ids_in_html = set(re.findall(r'id="([^"]+)"', html))
    ids_in_js = set(re.findall(r'getElementById\\("([^"]+)"\\)', js))
    missing = ids_in_js - ids_in_html
    assert_true(not missing, f"missing ids in index.html: {sorted(missing)}")

    assert_true(
        '<script src="script.js"></script>' in html,
        "script.js reference exists",
    )

    return "frontend ok"


def main():
    results = []
    results.append(run_backend_smoke_tests())
    results.append(run_frontend_smoke_tests())
    print("PASS:", ", ".join(results))


if __name__ == "__main__":
    main()

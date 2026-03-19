import re
import sys
import os
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


def run_youtube_poc_flow_tests():
    assert_true(
        hasattr(server, "fetch_youtube_content_poc"),
        "fetch_youtube_content_poc exists",
    )
    assert_true(
        hasattr(server, "parse_cookies_from_browser_option"),
        "parse_cookies_from_browser_option exists",
    )

    original_subtitle = server.fetch_youtube_subtitles_ytdlp
    original_audio = server.transcribe_youtube_audio
    old_poc_mode = os.environ.get("YOUTUBE_POC_MODE")

    try:
        os.environ["YOUTUBE_POC_MODE"] = "1"

        audio_calls = {"count": 0}

        def fake_subtitle_ok(_url):
            return [{"text": "第一行"}, {"text": "第二行"}]

        def fake_audio_unused(_url):
            audio_calls["count"] += 1
            return "audio-should-not-run"

        server.fetch_youtube_subtitles_ytdlp = fake_subtitle_ok
        server.transcribe_youtube_audio = fake_audio_unused

        text, source, errors = server.fetch_youtube_content_poc(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "dQw4w9WgXcQ",
        )
        assert_equal(source, "subtitle", "poc prefers subtitle")
        assert_true("第一行" in text, "subtitle content returned")
        assert_equal(audio_calls["count"], 0, "audio not called when subtitle works")
        assert_true("audio_error" in errors, "audio error slot exists")

        def fake_subtitle_fail(_url):
            raise RuntimeError("subtitle-failed")

        def fake_audio_ok(_url):
            audio_calls["count"] += 1
            return "audio-transcript-ok"

        server.fetch_youtube_subtitles_ytdlp = fake_subtitle_fail
        server.transcribe_youtube_audio = fake_audio_ok

        text, source, errors = server.fetch_youtube_content_poc(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "dQw4w9WgXcQ",
        )
        assert_equal(source, "audio", "poc falls back to audio")
        assert_equal(text, "audio-transcript-ok", "audio transcript returned")
        assert_true(errors["subtitle_error"] is not None, "subtitle error recorded")

        assert_equal(
            server.parse_cookies_from_browser_option("chrome"),
            ("chrome",),
            "parse cookies browser short format",
        )
        assert_equal(
            server.parse_cookies_from_browser_option("chrome:Profile 1"),
            ("chrome", "Profile 1"),
            "parse cookies browser with profile",
        )

    finally:
        server.fetch_youtube_subtitles_ytdlp = original_subtitle
        server.transcribe_youtube_audio = original_audio
        if old_poc_mode is None:
            os.environ.pop("YOUTUBE_POC_MODE", None)
        else:
            os.environ["YOUTUBE_POC_MODE"] = old_poc_mode

    return "youtube poc ok"


def main():
    results = []
    results.append(run_backend_smoke_tests())
    results.append(run_frontend_smoke_tests())
    results.append(run_youtube_poc_flow_tests())
    print("PASS:", ", ".join(results))


if __name__ == "__main__":
    main()

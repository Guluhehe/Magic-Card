import json
from http.server import BaseHTTPRequestHandler

from server import (
    YouTubeTranscriptApi,
    build_twitter_summary,
    build_youtube_summary,
    extract_youtube_id,
    fetch_twitter_text,
    parse_cookie_header,
)


class handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0
        raw_body = self.rfile.read(content_length) if content_length else b""
        try:
            data = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid-json"}, 400)
            return

        url = data.get("url")
        platform = data.get("platform")
        if not url:
            self._send_json({"error": "URL is required"}, 400)
            return
        if not platform:
            self._send_json({"error": "Platform is required"}, 400)
            return

        try:
            if platform == "YouTube":
                video_id = extract_youtube_id(url)
                if not video_id:
                    self._send_json({"error": "Invalid YouTube URL"}, 400)
                    return

                try:
                    if hasattr(YouTubeTranscriptApi, "get_transcript"):
                        transcript_data = YouTubeTranscriptApi.get_transcript(
                            video_id,
                            languages=["zh-CN", "en"],
                        )
                    else:
                        raise AttributeError("get_transcript not available")
                except Exception:
                    if hasattr(YouTubeTranscriptApi, "list_transcripts"):
                        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                    else:
                        transcripts = YouTubeTranscriptApi().list(video_id)
                    transcript = transcripts.find_transcript(["zh-Hans", "zh-CN", "en"])
                    transcript_data = transcript.fetch()

                def extract_text(item):
                    if isinstance(item, dict):
                        return item.get("text", "")
                    if hasattr(item, "text"):
                        return item.text
                    return ""

                full_text = " ".join(
                    [extract_text(item) for item in transcript_data if extract_text(item)]
                )
                summary_data = build_youtube_summary(full_text)

                self._send_json(
                    {
                        "title": "YouTube 视频内容实时解析 (Real Prototype)",
                        "summary": summary_data.get("summary", ""),
                        "length": f"{len(full_text) // 1000}k 字符",
                        "confidence": "100% (Direct Extraction)",
                        "highlights": summary_data.get("highlights", []),
                    }
                )
                return

            if platform == "Twitter":
                twitter_cookies = data.get("twitter_cookies") or {}
                if isinstance(twitter_cookies, str):
                    twitter_cookies = parse_cookie_header(twitter_cookies)
                if not isinstance(twitter_cookies, dict):
                    twitter_cookies = {}
                if data.get("auth_token"):
                    twitter_cookies.setdefault("auth_token", data.get("auth_token"))
                if data.get("ct0"):
                    twitter_cookies.setdefault("ct0", data.get("ct0"))

                title, text, method = fetch_twitter_text(url, twitter_cookies)
                summary_data = build_twitter_summary(text)
                method_labels = {
                    "fixtweet": "FixTweet API（推荐）",
                    "syndication": "Syndication API（不稳定）",
                    "snscrape": "snscrape 抓取",
                    "playwright": "Playwright DOM 抓取（兜底）",
                }
                confidences = {
                    "fixtweet": "95%",
                    "syndication": "75%",
                    "snscrape": "80%",
                    "playwright": "60%",
                }
                method_label = method_labels.get(method, "未知方式")
                confidence = confidences.get(method, "70%")
                self._send_json(
                    {
                        "title": title,
                        "summary": summary_data.get("summary", ""),
                        "length": f"{len(text)} 字符",
                        "confidence": confidence,
                        "highlights": summary_data.get("highlights", []),
                    }
                )
                return

            self._send_json({"error": "Unsupported platform"}, 400)

        except Exception as exc:
            self._send_json({"error": "extraction-failed", "message": str(exc)}, 500)

"""
Vercel Serverless Function - Magic Card API
Delegates to the shared server module.
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Force Vercel fast-path
os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("SKIP_SLOW_METHODS", "1")


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            url = data.get('url', '')
            platform = data.get('platform', '')

            if not url or not platform:
                self._send_json(400, {"error": "bad-request", "message": "Missing url or platform"})
                return

            from server import (
                extract_youtube_id, extract_twitter_id,
                fetch_youtube_transcript, transcript_to_text,
                fetch_youtube_metadata, build_metadata_text,
                build_summary_with_fallback,
                fetch_twitter_text, build_twitter_summary,
                classify_youtube_error,
            )

            if platform == 'YouTube':
                video_id = extract_youtube_id(url)
                if not video_id:
                    self._send_json(400, {"error": "invalid-url", "message": "无效的 YouTube 链接"})
                    return

                full_text = ""
                source = None
                transcript_error = None
                metadata = None

                # Try transcript (concurrent Player + Lemnos)
                try:
                    transcript_data = fetch_youtube_transcript(video_id)
                    full_text = transcript_to_text(transcript_data)
                    if full_text:
                        source = "transcript"
                except Exception as exc:
                    transcript_error = exc

                # Fallback to metadata
                if not full_text:
                    try:
                        metadata = fetch_youtube_metadata(video_id, url)
                        full_text = build_metadata_text(metadata)
                        if full_text:
                            source = "metadata"
                    except Exception:
                        pass

                if not full_text:
                    category = classify_youtube_error(transcript_error)
                    self._send_json(500, {
                        "error": "extraction-failed",
                        "message": f"未能获取视频内容（{category}）: {transcript_error}",
                        "retryable": True,
                    })
                    return

                summary_data, used_llm = build_summary_with_fallback(full_text, "YouTube")
                title = (metadata or {}).get("title", "") or "YouTube 视频内容解析"

                self._send_json(200, {
                    "title": title,
                    "summary": summary_data.get("summary", ""),
                    "length": f"{max(1, len(full_text) // 1000)}k 字符" if source != "metadata" else f"{len(full_text)} 字符",
                    "confidence": ("100% (Transcript + AI)" if used_llm else "85%") if source == "transcript" else "50% (Metadata)",
                    "highlights": summary_data.get("highlights", []),
                    "source": source,
                })

            elif platform == 'Twitter':
                title, text, method = fetch_twitter_text(url, {})
                summary_data = build_twitter_summary(text)
                self._send_json(200, {
                    "title": title,
                    "summary": summary_data.get("summary", ""),
                    "length": f"{len(text)} 字符",
                    "confidence": "95%" if method == "fixtweet" else "75%",
                    "highlights": summary_data.get("highlights", []),
                    "source": method,
                })
            else:
                self._send_json(400, {"error": "unsupported-platform", "message": f"不支持的平台: {platform}"})

        except Exception as e:
            self._send_json(500, {
                "error": "extraction-failed",
                "message": str(e),
                "retryable": "timeout" in str(e).lower() or "rate" in str(e).lower(),
            })

    def _send_json(self, status, data):
        self.send_response(status)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

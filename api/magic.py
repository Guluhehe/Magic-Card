"""
Vercel Serverless Function - Magic Card API (Gemini Route)
Uses Gemini for YouTube when available, falls back to transcript extraction.
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("SKIP_SLOW_METHODS", "1")

API_VERSION = "3.0.0"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "version": API_VERSION,
            "gemini_enabled": bool(os.getenv("GEMINI_API_KEY")),
        }, ensure_ascii=False).encode())

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
            )

            if platform == 'YouTube':
                result = self._parse_youtube(url, extract_youtube_id,
                                             fetch_youtube_transcript, transcript_to_text,
                                             fetch_youtube_metadata, build_metadata_text,
                                             build_summary_with_fallback)
                self._send_json(200, result)

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
                "retryable": "timeout" in str(e).lower(),
            })

    def _parse_youtube(self, url, extract_id, fetch_transcript, to_text,
                       fetch_meta, build_meta_text, summarize):
        video_id = extract_id(url)
        if not video_id:
            raise ValueError("无效的 YouTube 链接")

        full_text = ""
        source = None
        metadata = None

        # 1. Try Gemini direct (if key available)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                result = self._gemini_summarize(url, video_id, gemini_key)
                if result:
                    return result
            except Exception:
                pass  # Fall through to transcript

        # 2. Try transcript extraction
        try:
            transcript_data = fetch_transcript(video_id)
            full_text = to_text(transcript_data)
            if full_text:
                source = "transcript"
        except Exception:
            pass

        # 3. Fallback to metadata
        if not full_text:
            try:
                metadata = fetch_meta(video_id, url)
                full_text = build_meta_text(metadata)
                if full_text:
                    source = "metadata"
            except Exception:
                pass

        if not full_text:
            raise RuntimeError("未能获取视频内容，请确认视频有字幕或描述信息")

        summary_data, used_llm = summarize(full_text, "YouTube")
        title = (metadata or {}).get("title", "") or "YouTube 视频内容解析"

        return {
            "title": title,
            "summary": summary_data.get("summary", ""),
            "length": f"{max(1, len(full_text) // 1000)}k 字符" if source != "metadata" else f"{len(full_text)} 字符",
            "confidence": f"{'100%' if used_llm else '85%'} ({source})",
            "highlights": summary_data.get("highlights", []),
            "source": source,
        }

    def _gemini_summarize(self, url, video_id, api_key):
        try:
            import google.generativeai as genai
        except ImportError:
            return None

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        model = genai.GenerativeModel(model_name)

        prompt = (
            f"请分析这个 YouTube 视频并用中文生成总结。视频链接：{url}\n\n"
            "返回 JSON 格式：{\"summary\":\"2-3句核心观点\",\"highlights\":[{\"label\":\"要点\",\"text\":\"...\"}]}\n"
            "highlights 最多3条，label 要简短。"
        )

        response = model.generate_content(prompt)
        content = (response.text or "").strip()

        # Try to extract JSON
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            return None

        data = json.loads(content[start:end + 1])
        summary = data.get("summary", "").strip()
        highlights = []
        for item in data.get("highlights", []):
            if isinstance(item, dict) and item.get("label") and item.get("text"):
                highlights.append({"label": item["label"], "text": item["text"]})

        if not summary:
            return None

        return {
            "title": f"YouTube 视频解析 (Gemini)",
            "summary": summary,
            "length": f"Video {video_id}",
            "confidence": f"95% (Gemini {model_name})",
            "highlights": highlights[:3],
            "source": "gemini",
        }

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

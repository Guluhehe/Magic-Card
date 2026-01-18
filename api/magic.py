"""
Vercel Serverless Function - Magic Card API (Gemini Only)
Version: 3.0.0 - Clean Implementation
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests - Gemini ONLY"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            url = data.get('url', '')
            platform = data.get('platform', '')
            
            if not url:
                self._send_json(400, {"error": "Missing URL"})
                return
                
            # Import server functions
            from server import (
                extract_youtube_id,
                extract_twitter_id,
                fetch_twitter_text,
                build_twitter_summary
            )
            
            # Process based on platform
            result = {}
            if platform == 'YouTube':
                result = self._parse_youtube_gemini(url, extract_youtube_id)
            elif platform == 'Twitter':
                result = self._parse_twitter(url, extract_twitter_id,
                                            fetch_twitter_text,
                                            build_twitter_summary)
            else:
                self._send_json(400, {"error": "Unsupported platform"})
                return
            
            self._send_json(200, result)
            
        except Exception as e:
            import traceback
            self._send_json(500, {
                "error": "extraction-failed",
                "message": str(e),
                "detail": traceback.format_exc()[:500]
            })
    
    def _parse_youtube_gemini(self, url, extract_id):
        """Parse YouTube video using Gemini API ONLY"""
        video_id = extract_id(url)
        if not video_id:
            raise ValueError("无效的 YouTube 链接")
        
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("未配置 GEMINI_API_KEY")
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=gemini_key)
            # HARDCODED: gemini-2.0-flash (Verified available)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            prompt = f"""请分析这个 YouTube 视频并生成中文总结：
视频链接：{url}

请提供：
1. **核心观点**：用 2-3 句话概括视频的主要内容
2. **关键亮点**：列出 3-5 个最重要的要点
3. **适用场景**：这个视频适合哪些人观看？

请用中文回答，格式如下：

【核心观点】
...

【关键亮点】
1. ...
2. ...
3. ...

【适用场景】
..."""
            
            # Call Gemini
            response = model.generate_content([prompt, url])
            full_text = response.text
            
            # Parse
            summary = self._extract_section(full_text, "【核心观点】")
            highlights_text = self._extract_section(full_text, "【关键亮点】")
            
            highlights = []
            if highlights_text:
                for line in highlights_text.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith(('-', '•', '·'))):
                        text = re.sub(r'^[\d\-•·.\s]+', '', line).strip()
                        if text:
                            highlights.append({"label": "要点", "text": text})
            
            return {
                "title": "YouTube 视频解析 (Gemini AI)",
                "summary": summary.strip() if summary else full_text[:200],
                "length": f"视频 ID: {video_id}",
                "confidence": "100%",
                "highlights": highlights[:5]
            }
            
        except Exception as e:
            raise RuntimeError(f"Gemini 失败: {str(e)}")

    def _extract_section(self, text, marker):
        if marker not in text: return ""
        start = text.find(marker) + len(marker)
        next_marker = text.find("【", start)
        return text[start:next_marker].strip() if next_marker != -1 else text[start:].strip()

    def _parse_twitter(self, url, extract_id, fetch_text, build_summary):
        tweet_id = extract_id(url)
        title, text, method = fetch_text(url, {})
        summary_data = build_summary(text)
        return {
            "title": title,
            "summary": summary_data.get("summary", ""),
            "length": f"{len(text)} 字符",
            "confidence": "90%",
            "highlights": summary_data.get("highlights", [])
        }
    
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

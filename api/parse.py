"""
Vercel Serverless Function - Magic Card API (Enhanced with Gemini)
Version: 2.0.0 - Gemini Pro Integration
Last Updated: 2026-01-18
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Force Vercel to rebuild - Version 2.0.0
API_VERSION = "2.0.0-gemini-pro"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Return API version info"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        info = {
            "version": API_VERSION,
            "platform": "Vercel Serverless",
            "gemini_enabled": bool(os.getenv("GEMINI_API_KEY")),
            "default_model": os.getenv("GEMINI_MODEL", "gemini-pro")
        }
        
        self.wfile.write(json.dumps(info, ensure_ascii=False).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests - full implementation with Gemini"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            url = data.get('url', '')
            platform = data.get('platform', '')
            
            if not url or not platform:
                self._send_json(400, {
                    "error": "bad-request",
                    "message": "Missing url or platform"
                })
                return
            
            # Import server functions
            from server import (
                extract_youtube_id,
                extract_twitter_id,
                fetch_twitter_text,
                build_twitter_summary
            )
            
            # Process based on platform
            if platform == 'YouTube':
                result = self._parse_youtube_with_gemini(url, extract_youtube_id)
            elif platform == 'Twitter':
                result = self._parse_twitter(url, extract_twitter_id,
                                            fetch_twitter_text,
                                            build_twitter_summary)
            else:
                self._send_json(400, {
                    "error": "bad-request",
                    "message": f"Unsupported platform: {platform}"
                })
                return
            
            self._send_json(200, result)
            
        except Exception as e:
            self._send_json(500, {
                "error": "extraction-failed",
                "message": str(e),
                "api_version": API_VERSION
            })
    
    def _parse_youtube_with_gemini(self, url, extract_id):
        """Parse YouTube video using Gemini API (NO transcript download!)"""
        # Extract video ID
        video_id = extract_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # ONLY use Gemini - no fallback to transcripts
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("未配置 GEMINI_API_KEY。YouTube 功能需要 Gemini API。")
        
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=gemini_key)
            # Use gemini-pro - most stable
            # HARDCODED: gemini-pro only (gemini-1.5-flash not available)
            model = genai.GenerativeModel("gemini-pro")
            # Generate summary
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
            
            response = model.generate_content([prompt, url])
            full_text = response.text
            
            # Parse response
            summary = self._extract_gemini_section(full_text, "【核心观点】")
            highlights_text = self._extract_gemini_section(full_text, "【关键亮点】")
            scenario_text = self._extract_gemini_section(full_text, "【适用场景】")
            
            highlights = []
            if highlights_text:
                for line in highlights_text.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith(('-', '•', '·'))):
                        text = re.sub(r'^[\d\-•·.\s]+', '', line).strip()
                        if text:
                            highlights.append({"label": "要点", "text": text})
            
            if scenario_text:
                highlights.append({"label": "适用场景", "text": scenario_text.strip()})
            
            return {
                "title": f"YouTube 视频解析 (Gemini Pro)",
                "summary": summary.strip() if summary else full_text[:200],
                "length": f"视频 ID: {video_id}",
                "confidence": "95% (Gemini AI)",
                "highlights": highlights[:5]
            }
            
        except Exception as e:
            # Gemini failed, return detailed error
            import traceback
            error_detail = traceback.format_exc()
            raise RuntimeError(
                f"Gemini API 调用失败: {str(e)}\n\n"
                f"错误类型: {type(e).__name__}\n\n"
                f"模型: gemini-pro\n\n"
                f"详细: {error_detail[:300]}"
            )
    
    def _extract_gemini_section(self, text, marker):
        """Extract section from Gemini response"""
        if marker not in text:
            return ""
        
        start = text.find(marker) + len(marker)
        next_marker = text.find("【", start)
        
        if next_marker == -1:
            return text[start:].strip()
        else:
            return text[start:next_marker].strip()
    
    def _parse_twitter(self, url, extract_id, fetch_text, build_summary):
        """Parse Twitter/X post"""
        tweet_id = extract_id(url)
        if not tweet_id:
            raise ValueError("Invalid Twitter URL")
        
        title, text, method = fetch_text(url, {})
        summary_data = build_summary(text)
        
        confidences = {
            "fixtweet": "95%",
            "syndication": "75%",
            "snscrape": "80%",
            "playwright": "60%",
        }
        
        return {
            "title": title,
            "summary": summary_data.get("summary", ""),
            "length": f"{len(text)} 字符",
            "confidence": confidences.get(method, "70%"),
            "highlights": summary_data.get("highlights", [])
        }
    
    def _send_json(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))

    
    def _set_cors_headers(self):
        """Set CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

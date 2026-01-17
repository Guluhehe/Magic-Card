"""
Vercel Serverless Function - YouTube/Twitter Content Parser
纯 HTTP Handler 实现，不依赖 Flask
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add parent directory to import server modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import only the functions we need from server.py
try:
    from server import (
        extract_youtube_id,
        extract_twitter_id,
        fetch_youtube_transcript,
        transcript_to_text,
        build_youtube_summary,
        fetch_twitter_text,
        build_twitter_summary
    )
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    # Define fallback functions if import fails
    def extract_youtube_id(url):
        import re
        pattern = r'(?:v=|/)([0-9A-Za-z_-]{11}).*'
        match = re.search(pattern, url)
        return match.group(1) if match else None
    
    def extract_twitter_id(url):
        from urllib.parse import urlparse
        try:
            path = urlparse(url).path
            segments = [s for s in path.split("/") if s]
            if len(segments) >= 3 and segments[1] == "status":
                return segments[2]
            return None
        except:
            return None


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function Handler"""
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to /api/index"""
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error(400, "Empty request body")
                return
            
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            url = data.get('url')
            platform = data.get('platform')
            
            if not url or not platform:
                self._send_error(400, "Missing url or platform")
                return
            
            # Process based on platform
            if platform == 'YouTube':
                result = self._parse_youtube(url)
            elif platform == 'Twitter':
                result = self._parse_twitter(url)
            else:
                self._send_error(400, f"Unsupported platform: {platform}")
                return
            
            # Send successful response
            self._send_json(200, result)
            
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON")
        except Exception as e:
            self._send_error(500, str(e))
    
    def _parse_youtube(self, url):
        """Parse YouTube video"""
        try:
            video_id = extract_youtube_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            
            # Get transcript
            transcript_data = fetch_youtube_transcript(video_id)
            full_text = transcript_to_text(transcript_data)
            
            if not full_text:
                raise RuntimeError("未能获取字幕")
            
            # Get AI summary
            summary_data = build_youtube_summary(full_text)
            
            return {
                "title": "YouTube 视频内容实时解析",
                "summary": summary_data.get("summary", ""),
                "length": f"{len(full_text) // 1000}k 字符",
                "confidence": "100% (Direct Extraction)",
                "highlights": summary_data.get("highlights", [])
            }
            
        except Exception as e:
            raise RuntimeError(f"YouTube 解析失败: {str(e)}")
    
    def _parse_twitter(self, url):
        """Parse Twitter/X post"""
        try:
            tweet_id = extract_twitter_id(url)
            if not tweet_id:
                raise ValueError("Invalid Twitter URL")
            
            # Get tweet text
            title, text, method = fetch_twitter_text(url, {})
            summary_data = build_twitter_summary(text)
            
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
            
        except Exception as e:
            raise RuntimeError(f"Twitter 解析失败: {str(e)}")
    
    def _send_json(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))
    
    def _send_error(self, status_code, message):
        """Send error response"""
        self._send_json(status_code, {
            "error": "extraction-failed" if status_code == 500 else "bad-request",
            "message": message
        })
    
    def _set_cors_headers(self):
        """Set CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

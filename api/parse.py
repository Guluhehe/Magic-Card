"""
Vercel Serverless Function - Magic Card API
完整的 YouTube/Twitter 内容解析和 AI 总结
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests - full implementation"""
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
                fetch_youtube_transcript,
                transcript_to_text,
                build_youtube_summary,
                fetch_twitter_text,
                build_twitter_summary
            )
            
            # Process based on platform
            if platform == 'YouTube':
                result = self._parse_youtube(url, extract_youtube_id, 
                                            fetch_youtube_transcript,
                                            transcript_to_text,
                                            build_youtube_summary)
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
                "message": str(e)
            })
    
    def _parse_youtube(self, url, extract_id, fetch_transcript, to_text, build_summary):
        """Parse YouTube video"""
        # Extract video ID
        video_id = extract_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # Get transcript
        transcript_data = fetch_transcript(video_id)
        full_text = to_text(transcript_data)
        
        if not full_text:
            raise RuntimeError("未能获取字幕")
        
        # Get AI summary
        summary_data = build_summary(full_text)
        
        return {
            "title": "YouTube 视频内容实时解析",
            "summary": summary_data.get("summary", ""),
            "length": f"{len(full_text) // 1000}k 字符",
            "confidence": "100% (Direct Extraction)",
            "highlights": summary_data.get("highlights", [])
        }
    
    def _parse_twitter(self, url, extract_id, fetch_text, build_summary):
        """Parse Twitter/X post"""
        # Extract tweet ID
        tweet_id = extract_id(url)
        if not tweet_id:
            raise ValueError("Invalid Twitter URL")
        
        # Get tweet text
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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

"""
Vercel Debug - Test YouTube transcript directly
测试 YouTube 字幕是否真的能获取
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            video_id = data.get('video_id', 'dQw4w9WgXcQ')
            
            # Import and test
            from server import (
                fetch_youtube_transcript_player,
                get_preferred_transcript_languages
            )
            
            languages = get_preferred_transcript_languages()
            
            # Try Player API
            try:
                transcript = fetch_youtube_transcript_player(video_id, languages)
                result = {
                    "status": "success",
                    "method": "Player API",
                    "transcript_length": len(transcript),
                    "first_items": transcript[:3] if transcript else [],
                    "message": "字幕获取成功！"
                }
            except Exception as e:
                result = {
                    "status": "error",
                    "method": "Player API",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error = {
                "status": "fatal_error",
                "message": str(e)
            }
            
            self.wfile.write(json.dumps(error).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

"""
Vercel Serverless Function - Progressive Debug Version
逐步测试导入和功能
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
        """Handle POST requests"""
        try:
            # Step 1: Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            url = data.get('url', '')
            platform = data.get('platform', '')
            
            # Step 2: Try to import server functions
            try:
                from server import (
                    extract_youtube_id,
                    fetch_youtube_transcript,
                    transcript_to_text
                )
                import_status = "✅ Import successful"
            except Exception as e:
                import_status = f"❌ Import failed: {str(e)}"
                self._send_json(200, {
                    "status": "debug",
                    "import_status": import_status,
                    "received_url": url,
                    "received_platform": platform,
                    "python_version": sys.version,
                    "sys_path": sys.path[:3]
                })
                return
            
            # Step 3: Try to parse URL
            if platform == 'YouTube':
                video_id = extract_youtube_id(url)
                
                result = {
                    "status": "debug",
                    "import_status": import_status,
                    "video_id": video_id,
                    "next_step": "Will try to fetch transcript..."
                }
            else:
                result = {
                    "status": "debug",
                    "import_status": import_status,
                    "message": f"Platform {platform} not tested yet"
                }
            
            self._send_json(200, result)
            
        except Exception as e:
            self._send_json(500, {
                "error": "debug-error",
                "message": str(e),
                "type": type(e).__name__
            })
    
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

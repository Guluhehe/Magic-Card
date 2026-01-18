from http.server import BaseHTTPRequestHandler
import json
import os
import google.generativeai as genai

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                self.wfile.write(json.dumps({"error": "No API Key"}).encode())
                return

            genai.configure(api_key=api_key)
            
            models = []
            for m in genai.list_models():
                models.append({
                    "name": m.name,
                    "supported_methods": m.supported_generation_methods
                })
                
            self.wfile.write(json.dumps({
                "available_models": models,
                "library_version": genai.__version__
            }, indent=2).encode())
            
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode())

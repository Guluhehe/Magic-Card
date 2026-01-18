"""
Test Gemini configuration on Vercel
"""
from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test Gemini API configuration"""
        try:
            # Check if key is configured
            gemini_key = os.getenv("GEMINI_API_KEY")
            
            result = {
                "gemini_configured": bool(gemini_key),
                "gemini_key_length": len(gemini_key) if gemini_key else 0,
                "gemini_key_prefix": gemini_key[:10] + "..." if gemini_key else "Not set",
                "gemini_model": os.getenv("GEMINI_MODEL", "Not set"),
            }
            
            # Try to import the library
            try:
                import google.generativeai as genai
                result["genai_library"] = "✅ Imported successfully"
                result["genai_version"] = getattr(genai, '__version__', 'Unknown')
                
                # Try to configure (won't work without valid key, but tests the API)
                if gemini_key:
                    try:
                        genai.configure(api_key=gemini_key)
                        result["genai_configured"] = "✅ API configured"
                    except Exception as e:
                        result["genai_configured"] = f"⚠️ Config error: {str(e)}"
                        
            except ImportError as e:
                result["genai_library"] = f"❌ Import failed: {str(e)}"
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error = {
                "error": str(e),
                "type": type(e).__name__
            }
            
            self.wfile.write(json.dumps(error).encode())

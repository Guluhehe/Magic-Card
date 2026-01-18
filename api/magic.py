"""
Vercel Serverless Function - Magic Card API (Refined Logic)
Inspired by: YoutubeSummarizer, AI-Video-Summarizer, Concise
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import re
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

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
            
            if not url:
                self._send_json(400, {"error": "Missing URL"})
                return
            
            from server import (
                extract_youtube_id,
                extract_twitter_id,
                fetch_twitter_text,
                build_twitter_summary
            )
            
            if platform == 'YouTube':
                result = self._parse_youtube_refined(url, extract_youtube_id)
            elif platform == 'Twitter':
                result = self._parse_twitter(url, extract_twitter_id, fetch_twitter_text, build_twitter_summary)
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

    def _get_youtube_metadata(self, video_id):
        """Fetch video title and description without API key (Robust method)"""
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            html = response.text
            
            # Extract title using regex
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else "YouTube Video"
            
            # Extract description using regex
            desc_match = re.search(r'"shortDescription":"(.*?)"', html)
            description = desc_match.group(1).encode().decode('unicode-escape') if desc_match else ""
            
            return {"title": title, "description": description}
        except:
            return {"title": "Unknown Title", "description": ""}

    def _parse_youtube_refined(self, url, extract_id):
        """Refined YouTube parsing: Metadata + Best-effort Transcript"""
        video_id = extract_id(url)
        if not video_id:
            raise ValueError("无效的 YouTube 链接")
        
        # 1. Get Metadata (This almost always works)
        meta = self._get_youtube_metadata(video_id)
        
        # 2. Try to get Transcript (Best effort)
        transcript = ""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            # We try to get transcript, if it fails, we still have metadata
            entries = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-Hans', 'zh', 'en'])
            transcript = " ".join([e['text'] for e in entries])
        except Exception:
            # If transcript fails (often on Vercel), we'll rely on Title + Description
            pass
            
        # 3. Call Gemini with TEXT, not URL
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("未配置 GEMINI_API_KEY")
            
        content_to_analyze = f"标题: {meta['title']}\n描述: {meta['description']}\n\n"
        if transcript:
            content_to_analyze += f"字幕文本: {transcript[:15000]}" # Limit length
        else:
            content_to_analyze += "注: 无法获取字幕，请基于标题和描述进行深入分析。"

        return self._call_gemini_with_fallback(content_to_analyze, video_id)

    def _call_gemini_with_fallback(self, text, video_id):
        """Try multiple models to overcome quota issues"""
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Models to try in order
        models_to_try = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro", "gemini-pro-latest"]
        
        last_error = ""
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                prompt = "你是一个视频分析专家。请根据以下提取到的视频信息，生成一份简洁、高质量的中文总结卡片内容：\n\n" + text + "\n\n请按照以下格式回答：\n【核心观点】\n...\n【关键亮点】\n1. ...\n2. ...\n【适用场景】\n..."
                
                response = model.generate_content(prompt)
                full_text = response.text
                
                # Parse
                summary = self._extract_section(full_text, "【核心观点】")
                highlights_text = self._extract_section(full_text, "【关键亮点】")
                
                highlights = []
                if highlights_text:
                    for line in highlights_text.split('\n'):
                        line = line.strip()
                        if line and (line[0].isdigit() or line.startswith(('-', '•', '·'))):
                            clean_text = re.sub(r'^[\d\-•·.\s]+', '', line).strip()
                            if clean_text: highlights.append({"label": "点", "text": clean_text})
                
                return {
                    "title": "YouTube 视频分析 [AI精简版]",
                    "summary": summary.strip() if summary else full_text[:300],
                    "length": f"Video ID: {video_id}",
                    "confidence": f"AI ({model_name})",
                    "highlights": highlights[:5]
                }
            except Exception as e:
                last_error = str(e)
                continue # Try next model
        
        raise RuntimeError(f"所有 Gemini 模型均调用失败。最后一次错误: {last_error}")

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
            "confidence": "AI",
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

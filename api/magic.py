"""
Vercel Serverless Function - Magic Card API (OpenAI Version)
Using OpenAI GPT for reliable YouTube summarization
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import re
import requests

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
                result = self._parse_youtube_gpt(url, extract_youtube_id)
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
        """Fetch video title and description"""
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            html = response.text
            
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else "YouTube Video"
            
            desc_match = re.search(r'"shortDescription":"(.*?)"', html)
            description = desc_match.group(1).encode().decode('unicode-escape') if desc_match else ""
            
            return {"title": title, "description": description}
        except:
            return {"title": "Unknown Title", "description": ""}

    def _parse_youtube_gpt(self, url, extract_id):
        """Parse YouTube using OpenAI GPT"""
        video_id = extract_id(url)
        if not video_id:
            raise ValueError("无效的 YouTube 链接")
        
        # Get Metadata
        meta = self._get_youtube_metadata(video_id)
        
        # Try to get Transcript (best effort)
        transcript = ""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            entries = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-Hans', 'zh', 'en'])
            transcript = " ".join([e['text'] for e in entries])
        except:
            pass
            
        # Prepare content for GPT
        content = f"视频标题: {meta['title']}\n\n视频描述: {meta['description']}\n\n"
        if transcript:
            content += f"视频字幕文本:\n{transcript[:10000]}"  # Limit to 10k chars
        else:
            content += "注: 无法获取字幕，请基于标题和描述进行深度分析。"

        return self._call_openai(content, video_id)

    def _call_openai(self, text_content, video_id):
        """Call OpenAI GPT API"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("未配置 OPENAI_API_KEY")
        
        try:
            from openai import OpenAI
            
            # Support custom base_url (e.g., openkey.cloud)
            base_url = os.getenv("OPENAI_BASE_URL")
            
            # Create client with minimal params for compatibility
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                client = OpenAI(api_key=api_key)
            
            # Use GPT-4o-mini for cost efficiency
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            
            prompt = f"""你是一个专业的视频内容分析师。请根据以下视频信息，生成一份简洁、高质量的中文总结卡片。

{text_content}

请按照以下格式回答：

【核心观点】
用2-3句话概括视频的主要内容

【关键亮点】
1. 第一个重要观点
2. 第二个重要观点  
3. 第三个重要观点

【适用场景】
说明这个视频适合哪些人观看"""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的视频内容分析专家，擅长将长视频内容提炼为简洁的要点。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            full_text = response.choices[0].message.content
            
            # Parse response
            summary = self._extract_section(full_text, "【核心观点】")
            highlights_text = self._extract_section(full_text, "【关键亮点】")
            
            highlights = []
            if highlights_text:
                for line in highlights_text.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith(('-', '•', '·'))):
                        clean_text = re.sub(r'^[\d\-•·.\s]+', '', line).strip()
                        if clean_text:
                            highlights.append({"label": "亮点", "text": clean_text})
            
            return {
                "title": "YouTube 视频精华 [GPT分析]",
                "summary": summary.strip() if summary else full_text[:300],
                "length": f"Video ID: {video_id}",
                "confidence": f"AI ({model})",
                "highlights": highlights[:5]
            }
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API 调用失败: {str(e)}")

    def _extract_section(self, text, marker):
        if marker not in text:
            return ""
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

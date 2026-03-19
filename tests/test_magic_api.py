#!/usr/bin/env python3
"""
Local test script for api/magic.py logic
Tests YouTube metadata extraction and Gemini summarization
"""
import os
import sys
import json
import re
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def get_youtube_metadata(video_id):
    """Test metadata extraction"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        print(f"📥 Fetching metadata for video: {video_id}")
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', html)
        title = title_match.group(1).replace(" - YouTube", "") if title_match else "Unknown"
        
        # Extract description
        desc_match = re.search(r'"shortDescription":"(.*?)"', html)
        description = desc_match.group(1).encode().decode('unicode-escape') if desc_match else ""
        
        print(f"✅ Title: {title[:80]}...")
        print(f"✅ Description: {description[:100]}...")
        return {"title": title, "description": description}
    except Exception as e:
        print(f"❌ Metadata extraction failed: {e}")
        return {"title": "Error", "description": ""}

def test_gemini_with_text(text_content):
    """Test Gemini API with text content"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found in environment")
        return None
    
    print(f"🔑 API Key found: {gemini_key[:10]}...")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        # Try models in order
        models = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]
        
        for model_name in models:
            try:
                print(f"🤖 Trying model: {model_name}")
                model = genai.GenerativeModel(model_name)
                
                prompt = f"""你是视频分析专家。请根据以下信息生成简洁总结：

{text_content}

格式：
【核心观点】
...
【关键亮点】
1. ...
2. ...
"""
                
                response = model.generate_content(prompt)
                result = response.text
                
                print(f"✅ Model {model_name} succeeded!")
                print(f"📝 Response preview: {result[:200]}...")
                return {"model": model_name, "response": result}
                
            except Exception as e:
                print(f"⚠️ Model {model_name} failed: {str(e)[:100]}")
                continue
        
        print("❌ All models failed")
        return None
        
    except Exception as e:
        print(f"❌ Gemini import/config failed: {e}")
        return None

def main():
    print("=" * 60)
    print("🧪 Testing Magic API Logic Locally")
    print("=" * 60)
    
    # Test video
    video_id = "jNQXAC9IVRw"
    print(f"\n📹 Test Video: https://www.youtube.com/watch?v={video_id}")
    
    # Step 1: Test metadata extraction
    print("\n" + "="*60)
    print("Step 1: Metadata Extraction Test")
    print("="*60)
    meta = get_youtube_metadata(video_id)
    
    if not meta or meta["title"] == "Error":
        print("❌ Metadata test FAILED - Cannot proceed")
        return 1
    
    # Step 2: Test Gemini
    print("\n" + "="*60)
    print("Step 2: Gemini API Test")
    print("="*60)
    
    content = f"标题: {meta['title']}\n描述: {meta['description'][:500]}"
    result = test_gemini_with_text(content)
    
    if not result:
        print("❌ Gemini test FAILED")
        return 1
    
    # Final report
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print(f"✓ Metadata extraction: OK")
    print(f"✓ Gemini model used: {result['model']}")
    print(f"✓ Response length: {len(result['response'])} chars")
    print("\n🚀 Logic is ready for deployment!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

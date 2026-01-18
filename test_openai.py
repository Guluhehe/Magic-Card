#!/usr/bin/env python3
"""Quick test for OpenAI-based YouTube parser"""
import os
import sys
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

def test_openai_youtube():
    print("="*60)
    print("🧪 Testing OpenAI YouTube Parser")
    print("="*60)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        print("💡 Set it in .env file or environment")
        return 1
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Test metadata extraction
    video_id = "jNQXAC9IVRw"
    print(f"\n📹 Test video: {video_id}")
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        title_match = re.search(r'<title>(.*?)</title>', html)
        title = title_match.group(1).replace(" - YouTube", "") if title_match else "NOT_FOUND"
        
        desc_match = re.search(r'"shortDescription":"(.*?)"', html)
        description = desc_match.group(1) if desc_match else "NOT_FOUND"
        
        print(f"✅ Title: {title[:60]}...")
        print(f"✅ Description: {description[:80]}...")
        
    except Exception as e:
        print(f"❌ Metadata fetch failed: {e}")
        return 1
    
    # Test OpenAI call
    print("\n🤖 Testing OpenAI API...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        test_content = f"标题: {title}\n描述: {description[:200]}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是视频分析专家"},
                {"role": "user", "content": f"请用中文简单总结:\n{test_content}"}
            ],
            max_tokens=100
        )
        
        result = response.choices[0].message.content
        print(f"✅ OpenAI response: {result[:100]}...")
        
    except Exception as e:
        print(f"❌ OpenAI call failed: {e}")
        return 1
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\n🚀 Ready for production deployment")
    return 0

if __name__ == "__main__":
    sys.exit(test_openai_youtube())

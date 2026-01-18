#!/usr/bin/env python3
"""
Dry-run test: Tests core logic without calling Gemini API
Tests metadata extraction and validates code structure
"""
import os
import sys
import json
import re
import requests

sys.path.insert(0, os.path.dirname(__file__))

def test_metadata_extraction():
    """Test YouTube metadata extraction"""
    print("="*60)
    print("Test 1: YouTube Metadata Extraction")
    print("="*60)
    
    test_videos = [
        "jNQXAC9IVRw",  # Me at the zoo
        "dQw4w9WgXcQ",  # Rick Roll
    ]
    
    for video_id in test_videos:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            print(f"\n📹 Testing: {video_id}")
            response = requests.get(url, headers=headers, timeout=10)
            html = response.text
            
            # Title
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else "NOT_FOUND"
            
            # Description
            desc_match = re.search(r'"shortDescription":"(.*?)"', html)
            description = desc_match.group(1) if desc_match else "NOT_FOUND"
            
            print(f"  ✅ Title: {title[:60]}...")
            print(f"  ✅ Desc length: {len(description)} chars")
            
            if title == "NOT_FOUND" or description == "NOT_FOUND":
                print(f"  ⚠️ Some fields missing")
                return False
                
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            return False
    
    return True

def test_imports():
    """Test that required libraries can be imported"""
    print("\n" + "="*60)
    print("Test 2: Required Libraries Check")
    print("="*60)
    
    libs = {
        "requests": None,
        "google.generativeai": None,
        "youtube_transcript_api": None,
    }
    
    for lib_name in libs:
        try:
            if lib_name == "google.generativeai":
                import google.generativeai
                libs[lib_name] = "✅"
            elif lib_name == "youtube_transcript_api":
                from youtube_transcript_api import YouTubeTranscriptApi
                libs[lib_name] = "✅"
            elif lib_name == "requests":
                import requests
                libs[lib_name] = "✅"
        except ImportError:
            libs[lib_name] = "❌ NOT INSTALLED"
    
    for lib, status in libs.items():
        print(f"  {lib}: {status}")
    
    all_ok = all(s == "✅" for s in libs.values())
    return all_ok

def test_api_magic_structure():
    """Validate api/magic.py structure"""
    print("\n" + "="*60)
    print("Test 3: API Magic File Structure")
    print("="*60)
    
    magic_file = "api/magic.py"
    
    if not os.path.exists(magic_file):
        print(f"  ❌ {magic_file} not found!")
        return False
    
    with open(magic_file, 'r') as f:
        content = f.read()
    
    required_methods = [
        "_get_youtube_metadata",
        "_parse_youtube_refined", 
        "_call_gemini_with_fallback",
        "do_POST",
    ]
    
    for method in required_methods:
        if method in content:
            print(f"  ✅ Method found: {method}")
        else:
            print(f"  ❌ Missing method: {method}")
            return False
    
    return True

def main():
    print("\n🧪 DRY-RUN TEST (No API calls)")
    print("="*60)
    
    results = {
        "Metadata Extraction": test_metadata_extraction(),
        "Required Libraries": test_imports(),
        "API Structure": test_api_magic_structure(),
    }
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Ready for deployment!")
        print("="*60)
        print("\n📝 Next steps:")
        print("1. Ensure GEMINI_API_KEY is set in Vercel")
        print("2. Deploy and test on production")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Please fix before deployment")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())

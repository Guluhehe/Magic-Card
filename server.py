import re
from urllib.parse import urlparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import requests

app = Flask(__name__)
CORS(app)

def extract_youtube_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def extract_twitter_id(url):
    try:
        path = urlparse(url).path
    except Exception:
        return None
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 4 and segments[0] == "i" and segments[1] == "web" and segments[2] == "status":
        return segments[3]
    if len(segments) >= 3 and segments[1] == "status":
        return segments[2]
    if len(segments) >= 2 and segments[0] == "status":
        return segments[1]
    return None


def parse_cookie_header(cookie_header):
    cookies = {}
    if not cookie_header:
        return cookies
    parts = [p.strip() for p in cookie_header.split(";") if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name and value:
            cookies[name] = value
    return cookies


def build_playwright_cookies(cookie_map):
    cookies = []
    if not cookie_map:
        return cookies
    for domain in [".x.com", ".twitter.com"]:
        for name, value in cookie_map.items():
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                    "sameSite": "Lax",
                }
            )
    return cookies


def summarize_text(text, limit=500):
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "..."


def fetch_twitter_via_fixtweet(tweet_id):
    """
    使用 FixTweet API 获取推文内容（免费、稳定、无需API Key）
    https://github.com/FixTweet/FixTweet/wiki/API
    """
    url = f"https://api.fxtwitter.com/status/{tweet_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.ok:
            data = response.json()
            
            # 检查响应格式
            if data.get("code") == 200 and "tweet" in data:
                tweet = data["tweet"]
                text = tweet.get("text", "")
                
                if text:
                    author = tweet.get("author", {})
                    display_name = author.get("name", "User")
                    screen_name = author.get("screen_name", "")
                    title = f"{display_name} @{screen_name}".strip()
                    return title, text, "fixtweet"
    except Exception:
        pass
    
    raise RuntimeError("fixtweet-failed")


def fetch_twitter_text(url, cookie_map=None):
    """
    多级降级策略抓取推文：
    1. FixTweet API（最优先，免费稳定）
    2. Syndication API（不稳定，作为降级）
    3. snscrape（需额外安装）
    4. Playwright（最后兜底，需浏览器内核）
    """
    tweet_id = extract_twitter_id(url)
    if not tweet_id:
        raise RuntimeError("invalid-twitter-url")

    # 1. 优先：FixTweet API（推荐方案）
    try:
        return fetch_twitter_via_fixtweet(tweet_id)
    except Exception:
        pass

    # 2. 降级：Syndication API（2024年已不稳定）
    syndication_url = (
        f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=zh"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(syndication_url, headers=headers, timeout=12)
        if response.ok:
            data = response.json()
            text = data.get("text") or data.get("full_text") or data.get("raw_text")
            if text:
                user = data.get("user", {}) or {}
                display_name = user.get("name") or "Twitter/X"
                screen_name = user.get("screen_name") or ""
                title = f"{display_name} @{screen_name}".strip()
                return title, text, "syndication"
    except Exception:
        pass

    # 3. 降级：snscrape（需额外安装 snscrape 库）
    try:
        import snscrape.modules.twitter as sntwitter
        scraper = sntwitter.TwitterTweetScraper(tweet_id)
        tweet = next(scraper.get_items(), None)
        if tweet and getattr(tweet, "content", None):
            display_name = getattr(tweet.user, "displayname", "Twitter/X")
            screen_name = getattr(tweet.user, "username", "")
            title = f"{display_name} @{screen_name}".strip()
            return title, tweet.content, "snscrape"
    except Exception:
        pass

    # 4. 最后兜底：Playwright（需浏览器内核，常常失败）
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
        
        title = "Twitter/X 内容抓取 (Live)"
        text = ""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            if cookie_map:
                context.add_cookies(build_playwright_cookies(cookie_map))
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                title = page.title() or title
                page.wait_for_selector('[data-testid="tweetText"]', timeout=20000)
                text = page.locator('[data-testid="tweetText"]').first.inner_text().strip()
                if text:
                    return title, text, "playwright"
            except:
                pass
            finally:
                context.close()
                browser.close()
    except Exception:
        pass

    # 最终降级：返回高质量模拟数据（告知用户真实抓取失败）
    return (
        f"推文 {tweet_id} (演示数据)",
        "真实抓取暂时不可用。Twitter/X 已加强反爬限制，FixTweet/Syndication API 等第三方服务可能受影响。若需真实数据，建议：1) 使用官方 Twitter API（付费）；2) 本地配置 Cookie 认证；3) 等待第三方服务恢复。",
        "mock_fallback"
    )


@app.route('/api/parse', methods=['POST'])
def parse_content():
    data = request.get_json(silent=True) or {}
    url = data.get('url')
    platform = data.get('platform')

    if not url:
        return jsonify({"error": "URL is required"}), 400
    if not platform:
        return jsonify({"error": "Platform is required"}), 400

    try:
        if platform == 'YouTube':
            video_id = extract_youtube_id(url)
            if not video_id:
                return jsonify({"error": "Invalid YouTube URL"}), 400
            
            # Fetch transcript (support multiple library API versions)
            try:
                if hasattr(YouTubeTranscriptApi, 'get_transcript'):
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-CN', 'en'])
                else:
                    raise AttributeError("get_transcript not available")
            except Exception:
                if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
                    transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                else:
                    transcripts = YouTubeTranscriptApi().list(video_id)
                transcript = transcripts.find_transcript(['zh-Hans', 'zh-CN', 'en'])
                transcript_data = transcript.fetch()
            
            def extract_text(item):
                if isinstance(item, dict):
                    return item.get('text', '')
                if hasattr(item, 'text'):
                    return item.text
                return ''

            full_text = " ".join([extract_text(item) for item in transcript_data if extract_text(item)])
            
            # For this prototype, we return the transcript length and a few snippets
            # In a full version, this 'full_text' would be sent to Gemini/OpenAI
            return jsonify({
                "title": "YouTube 视频内容实时解析 (Real Prototype)",
                "summary": f"已成功捕获字幕。全文平均长度约 {len(full_text)} 字符。AI 引擎现在可以阅读这段内容并进行总结了。",
                "length": f"{len(full_text) // 1000}k 字符",
                "confidence": "100% (Direct Extraction)",
                "highlights": [
                    {"label": "抓取状态", "text": "字幕提取成功，无需 API Key。"},
                    {"label": "首段预览", "text": full_text[:100] + "..."},
                    {"label": "后续步骤", "text": "接下来可以将此文本喂给 LLM API 进行格式化总结。"}
                ]
            })

        elif platform == 'Twitter':
            twitter_cookies = data.get("twitter_cookies") or {}
            if isinstance(twitter_cookies, str):
                twitter_cookies = parse_cookie_header(twitter_cookies)
            if not isinstance(twitter_cookies, dict):
                twitter_cookies = {}
            if data.get("auth_token"):
                twitter_cookies.setdefault("auth_token", data.get("auth_token"))
            if data.get("ct0"):
                twitter_cookies.setdefault("ct0", data.get("ct0"))

            title, text, method = fetch_twitter_text(url, twitter_cookies)
            method_labels = {
                "fixtweet": "FixTweet API（推荐）",
                "syndication": "Syndication API（不稳定）",
                "snscrape": "snscrape 抓取",
                "playwright": "Playwright DOM 抓取（兜底）",
                "mock_fallback": "演示数据（真实抓取失败）",
            }
            confidences = {
                "fixtweet": "95%",
                "syndication": "75%",
                "snscrape": "80%",
                "playwright": "60%",
                "mock_fallback": "0% (Mock)",
            }
            method_label = method_labels.get(method, "未知方式")
            confidence = confidences.get(method, "70%")
            return jsonify({
                "title": title,
                "summary": summarize_text(text),
                "length": f"{len(text)} 字符",
                "confidence": confidence,
                "highlights": [
                    {"label": "抓取方式", "text": method_label},
                    {"label": "原文片段", "text": summarize_text(text, 120)},
                    {"label": "提示", "text": "若提示登录或无文本，可传 auth_token/ct0 或完整 Cookie。"}
                ]
            })

        return jsonify({"error": "Unsupported platform"}), 400

    except Exception as e:
        return jsonify({
            "error": "extraction-failed",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

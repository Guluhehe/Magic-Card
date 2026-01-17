import html
import json
import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import requests

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional, env vars can be set manually
    pass


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

def is_debug_enabled():
    return os.getenv("TRANSCRIPT_DEBUG", "").lower() in ("1", "true", "yes")


def get_preferred_transcript_languages():
    env_langs = os.getenv("TRANSCRIPT_LANGS", "")
    if env_langs.strip():
        return [lang.strip() for lang in env_langs.split(",") if lang.strip()]
    return ["zh-Hans", "zh-CN", "zh", "zh-TW", "en", "en-US", "en-GB"]


def get_piped_instances():
    env_instances = os.getenv("PIPED_INSTANCES", "")
    if env_instances.strip():
        return [item.strip().rstrip("/") for item in env_instances.split(",") if item.strip()]
    return [
        "https://piped.video",
        "https://piped.mha.fi",
        "https://piped.lunar.icu",
        "https://vid.puffyan.us",
        "https://piped-api.kavin.rocks",
    ]


def parse_caption_text(raw_text):
    lines = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if "-->" in line:
            continue
        if re.match(r"^\d+$", line):
            continue
        lines.append(line)
    return [{"text": line} for line in lines]


def parse_caption_xml(raw_text):
    lines = []
    root = ET.fromstring(raw_text)
    for node in root.findall(".//text"):
        if node.text:
            lines.append(html.unescape(node.text.replace("\n", " ")).strip())
    return [{"text": line} for line in lines if line]


def parse_caption_payload(raw_text):
    text = raw_text.strip()
    if not text:
        return []
    if "WEBVTT" in text:
        return parse_caption_text(text)
    if text.startswith("<"):
        try:
            return parse_caption_xml(text)
        except Exception:
            return []
    return parse_caption_text(text)


def get_youtube_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept": "*/*",
    }


def fetch_youtube_transcript_timedtext(video_id, languages):
    headers = get_youtube_headers()
    bases = [
        "https://video.google.com/timedtext",
        "https://www.youtube.com/api/timedtext",
    ]
    errors = []

    for base in bases:
        list_url = f"{base}?type=list&v={video_id}"
        try:
            response = requests.get(list_url, headers=headers, timeout=10)
            if not response.ok:
                errors.append(RuntimeError(f"{list_url} -> {response.status_code}"))
                continue
            if not response.text.strip():
                errors.append(RuntimeError(f"{list_url} -> empty response"))
                continue
            root = ET.fromstring(response.text)
            tracks = root.findall("track")
            if not tracks:
                errors.append(RuntimeError(f"{list_url} -> empty tracks"))
                continue

            def pick_match():
                for lang in languages:
                    for track in tracks:
                        code = track.get("lang_code") or ""
                        if code.lower().startswith(lang.lower()):
                            return track
                return tracks[0]

            track = pick_match()
            lang_code = track.get("lang_code")
            name = track.get("name")
            kind = track.get("kind")
            if not lang_code:
                errors.append(RuntimeError(f"{list_url} -> missing lang_code"))
                continue
            caption_url = f"{base}?lang={quote(lang_code)}&v={video_id}&fmt=vtt"
            if name:
                caption_url = f"{caption_url}&name={quote(name)}"
            if kind:
                caption_url = f"{caption_url}&kind={quote(kind)}"
            response = requests.get(caption_url, headers=headers, timeout=10)
            if not response.ok:
                errors.append(RuntimeError(f"{caption_url} -> {response.status_code}"))
                continue
            transcript = parse_caption_payload(response.text)
            if transcript:
                return transcript
            errors.append(RuntimeError(f"{caption_url} -> empty transcript"))
        except Exception as exc:
            errors.append(exc)

    for base in bases:
        for lang in languages:
            for kind in ("", "asr"):
                caption_url = f"{base}?lang={quote(lang)}&v={video_id}&fmt=vtt"
                if kind:
                    caption_url = f"{caption_url}&kind={quote(kind)}"
                try:
                    response = requests.get(caption_url, headers=headers, timeout=10)
                    if not response.ok:
                        errors.append(RuntimeError(f"{caption_url} -> {response.status_code}"))
                        continue
                    transcript = parse_caption_payload(response.text)
                    if transcript:
                        return transcript
                    errors.append(RuntimeError(f"{caption_url} -> empty transcript"))
                except Exception as exc:
                    errors.append(exc)

    raise RuntimeError(f"{bases[0]} -> failed (timedtext errors: {errors})")


def fetch_youtube_transcript_piped(video_id, languages):
    instances = get_piped_instances()
    last_error = None
    errors = []
    for base in instances:
        try:
            meta_url = f"{base}/api/v1/captions/{video_id}"
            response = requests.get(meta_url, timeout=10)
            if not response.ok:
                last_error = RuntimeError(f"{meta_url} -> {response.status_code}")
                errors.append(last_error)
                continue
            payload = response.json()
            if isinstance(payload, dict) and "captions" in payload:
                captions = payload.get("captions", [])
            else:
                captions = payload if isinstance(payload, list) else []
            if not captions:
                last_error = RuntimeError(f"{meta_url} -> empty captions")
                errors.append(last_error)
                continue

            def pick_match():
                for lang in languages:
                    for track in captions:
                        code = (
                            track.get("languageCode")
                            or track.get("language")
                            or track.get("code")
                            or ""
                        )
                        label = (track.get("label") or "").lower()
                        if code.lower() == lang.lower() or label.startswith(lang.lower()):
                            return track
                return captions[0]

            track = pick_match()
            caption_url = track.get("url") or ""
            if not caption_url:
                last_error = RuntimeError(f"{meta_url} -> missing url")
                errors.append(last_error)
                continue
            if caption_url.startswith("/"):
                caption_url = f"{base}{caption_url}"
            response = requests.get(caption_url, timeout=10)
            if not response.ok:
                last_error = RuntimeError(f"{caption_url} -> {response.status_code}")
                errors.append(last_error)
                continue
            transcript = parse_caption_text(response.text)
            if transcript:
                return transcript
            last_error = RuntimeError(f"{caption_url} -> empty transcript")
            errors.append(last_error)
        except Exception as exc:
            last_error = exc
            errors.append(exc)
    if last_error:
        raise RuntimeError(f"{last_error} (piped errors: {errors})")
    raise RuntimeError("piped captions unavailable")


def fetch_youtube_transcript_lemnos(video_id, languages):
    meta_url = f"https://yt.lemnoslife.com/videos?part=captionTracks&id={video_id}"
    response = requests.get(meta_url, timeout=10)
    if not response.ok:
        raise RuntimeError(f"{meta_url} -> {response.status_code}")
    data = response.json()
    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"{meta_url} -> empty items")
    tracks = items[0].get("captionTracks") or []
    if not tracks:
        raise RuntimeError(f"{meta_url} -> empty captionTracks")

    def pick_match():
        for lang in languages:
            for track in tracks:
                code = track.get("languageCode") or ""
                if code.lower().startswith(lang.lower()):
                    return track
        return tracks[0]

    track = pick_match()
    caption_url = track.get("baseUrl") or ""
    if not caption_url:
        raise RuntimeError(f"{meta_url} -> missing baseUrl")
    if "fmt=" not in caption_url:
        sep = "&" if "?" in caption_url else "?"
        caption_url = f"{caption_url}{sep}fmt=vtt"
    response = requests.get(caption_url, timeout=10)
    if not response.ok:
        raise RuntimeError(f"{caption_url} -> {response.status_code}")
    transcript = parse_caption_text(response.text)
    if transcript:
        return transcript
    raise RuntimeError(f"{caption_url} -> empty transcript")


def fetch_youtube_transcript(video_id):
    languages = get_preferred_transcript_languages()
    debug = is_debug_enabled()
    last_error = None
    timedtext_error = None
    piped_error = None
    lemnos_error = None

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        try:
            return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        except Exception as exc:
            last_error = exc

    transcripts = None
    try:
        if hasattr(YouTubeTranscriptApi, "list_transcripts"):
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        else:
            transcripts = YouTubeTranscriptApi().list(video_id)
    except Exception as exc:
        last_error = exc

    if transcripts:
        for finder_name in ("find_manually_created_transcript", "find_generated_transcript", "find_transcript"):
            try:
                finder = getattr(transcripts, finder_name)
                transcript = finder(languages)
                return transcript.fetch()
            except Exception as exc:
                last_error = exc

        for transcript in transcripts:
            try:
                return transcript.fetch()
            except Exception as exc:
                last_error = exc

    try:
        return fetch_youtube_transcript_timedtext(video_id, languages)
    except Exception as exc:
        timedtext_error = exc

    try:
        return fetch_youtube_transcript_piped(video_id, languages)
    except Exception as exc:
        piped_error = exc

    try:
        return fetch_youtube_transcript_lemnos(video_id, languages)
    except Exception as exc:
        lemnos_error = exc

    message = "未能获取字幕，请确认视频字幕可用。"
    if debug:
        details = []
        if last_error:
            details.append(f"youtube_error={last_error}")
        if timedtext_error:
            details.append(f"timedtext_error={timedtext_error}")
        if piped_error:
            details.append(f"piped_error={piped_error}")
        if lemnos_error:
            details.append(f"lemnos_error={lemnos_error}")
        if details:
            message = f"{message} ({'; '.join(details)})"
    raise RuntimeError(message)


def transcript_to_text(transcript_data):
    def extract_text(item):
        if isinstance(item, dict):
            return item.get("text", "")
        if hasattr(item, "text"):
            return item.text
        return ""

    return " ".join([extract_text(item) for item in transcript_data if extract_text(item)])


def summarize_with_openai(text, platform):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    max_chars = int(os.getenv("SUMMARY_INPUT_CHARS", "12000"))
    snippet = text[:max_chars]

    system_prompt = (
        "你是内容总结助手，请用中文输出精简摘要，并给出 3 条要点。"
        "返回 JSON 格式：{\"summary\":\"...\",\"highlights\":[{\"label\":\"...\",\"text\":\"...\"}]}"
        "label 要简短。保留原文专有名词。"
    )
    user_prompt = f"平台：{platform}\n内容：{snippet}"

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.output_text
    except Exception:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
        except Exception:
            return None

    try:
        data = json.loads(content)
    except Exception:
        return None

    summary = str(data.get("summary", "")).strip()
    raw_highlights = data.get("highlights", [])
    if not summary or not isinstance(raw_highlights, list):
        return None

    highlights = []
    for item in raw_highlights:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        text_item = str(item.get("text", "")).strip()
        if label and text_item:
            highlights.append({"label": label, "text": text_item})

    if not highlights:
        return None

    return {"summary": summary, "highlights": highlights[:3]}


def build_youtube_summary(text):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("未配置 OPENAI_API_KEY，YouTube 总结需要 AI Key。")
    llm_summary = summarize_with_openai(text, "YouTube")
    if not llm_summary:
        raise RuntimeError("AI 总结失败，请检查 Key 或额度。")
    return llm_summary


def build_twitter_summary(text):
    summary = text.strip()
    return {"summary": summary, "highlights": []}


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

    raise RuntimeError("tweet-text-not-found")


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
            
            transcript_data = fetch_youtube_transcript(video_id)
            full_text = transcript_to_text(transcript_data)
            if not full_text:
                raise RuntimeError("未能获取字幕，请确认视频字幕可用。")
            summary_data = build_youtube_summary(full_text)

            # For this prototype, we return the transcript length and summary
            return jsonify({
                "title": "YouTube 视频内容实时解析 (Real Prototype)",
                "summary": summary_data.get("summary", ""),
                "length": f"{len(full_text) // 1000}k 字符",
                "confidence": "100% (Direct Extraction)",
                "highlights": summary_data.get("highlights", [])
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
            summary_data = build_twitter_summary(text)
            method_labels = {
                "fixtweet": "FixTweet API（推荐）",
                "syndication": "Syndication API（不稳定）",
                "snscrape": "snscrape 抓取",
                "playwright": "Playwright DOM 抓取（兜底）",
            }
            confidences = {
                "fixtweet": "95%",
                "syndication": "75%",
                "snscrape": "80%",
                "playwright": "60%",
            }
            method_label = method_labels.get(method, "未知方式")
            confidence = confidences.get(method, "70%")
            return jsonify({
                "title": title,
                "summary": summary_data.get("summary", ""),
                "length": f"{len(text)} 字符",
                "confidence": confidence,
                "highlights": summary_data.get("highlights", [])
            })

        return jsonify({"error": "Unsupported platform"}), 400

    except Exception as e:
        return jsonify({
            "error": "extraction-failed",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

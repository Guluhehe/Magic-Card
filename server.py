import html
import json
import os
import re
import tempfile
import time
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

_CACHE = {}
_CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
_CACHE_MAX_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "256"))


def cache_get(key):
    if _CACHE_TTL <= 0:
        return None
    item = _CACHE.get(key)
    if not item:
        return None
    value, ts = item
    if time.time() - ts > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return value


def cache_set(key, value):
    if _CACHE_TTL <= 0:
        return
    if _CACHE_MAX_ITEMS > 0 and len(_CACHE) >= _CACHE_MAX_ITEMS:
        oldest_key = min(_CACHE.items(), key=lambda item: item[1][1])[0]
        _CACHE.pop(oldest_key, None)
    _CACHE[key] = (value, time.time())

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


def extract_json_object(text, marker):
    idx = text.find(marker)
    if idx == -1:
        return None
    start = text.find("{", idx)
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "\"":
                in_str = False
        else:
            if ch == "\"":
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


def fetch_youtube_transcript_player(video_id, languages):
    headers = get_youtube_headers()
    cookies = {"CONSENT": "YES+cb.20210328-17-p0.en+FX+111"}
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    response = requests.get(watch_url, headers=headers, cookies=cookies, timeout=10)
    if not response.ok:
        raise RuntimeError(f"{watch_url} -> {response.status_code}")
    payload = extract_json_object(response.text, "ytInitialPlayerResponse")
    if not payload:
        raise RuntimeError(f"{watch_url} -> ytInitialPlayerResponse not found")
    try:
        data = json.loads(payload)
    except Exception as exc:
        raise RuntimeError(f"{watch_url} -> player json parse failed: {exc}")

    captions = (
        data.get("captions", {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks", [])
    )
    if not captions:
        raise RuntimeError(f"{watch_url} -> empty captionTracks")

    def pick_match():
        for lang in languages:
            for track in captions:
                code = track.get("languageCode") or ""
                if code.lower().startswith(lang.lower()):
                    return track
        return captions[0]

    track = pick_match()
    caption_url = track.get("baseUrl") or track.get("url")
    if not caption_url:
        raise RuntimeError(f"{watch_url} -> missing baseUrl")
    if "fmt=" not in caption_url:
        sep = "&" if "?" in caption_url else "?"
        caption_url = f"{caption_url}{sep}fmt=vtt"
    response = requests.get(caption_url, headers=headers, timeout=10)
    if not response.ok:
        raise RuntimeError(f"{caption_url} -> {response.status_code}")
    transcript = parse_caption_payload(response.text)
    if transcript:
        return transcript
    raise RuntimeError(f"{caption_url} -> empty transcript")


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
    """
    获取 YouTube 字幕 - 完全不依赖 youtube-transcript-api
    优先使用最快、最稳定的方法，适配 Vercel 环境
    """
    languages = get_preferred_transcript_languages()
    debug = is_debug_enabled()
    errors = []
    
    # 方法 1: Player API（最快、最稳定）
    try:
        return fetch_youtube_transcript_player(video_id, languages)
    except Exception as exc:
        errors.append(f"Player API: {exc}")
        if debug:
            print(f"[DEBUG] Player API failed: {exc}")
    
    # 方法 2: Lemnos API（第三方，但快）
    try:
        return fetch_youtube_transcript_lemnos(video_id, languages)
    except Exception as exc:
        errors.append(f"Lemnos API: {exc}")
        if debug:
            print(f"[DEBUG] Lemnos API failed: {exc}")
    
    # Vercel 环境：只尝试快速方法
    is_vercel = os.getenv("VERCEL") == "1"
    skip_slow = os.getenv("SKIP_SLOW_METHODS", "").lower() in ("1", "true", "yes")
    
    if is_vercel or skip_slow:
        # 在 Vercel 上放弃，避免超时
        message = "字幕获取失败（快速模式），请确认视频有字幕"
        if debug:
            message = f"{message}。尝试的方法: {'; '.join(errors)}"
        raise RuntimeError(message)
    
    # 方法 3: TimedText API（本地环境可以retry）
    try:
        return fetch_youtube_transcript_timedtext(video_id, languages)
    except Exception as exc:
        errors.append(f"TimedText API: {exc}")
        if debug:
            print(f"[DEBUG] TimedText API failed: {exc}")
    
    # 方法 4: Piped（最慢，本地环境最后尝试）
    try:
        return fetch_youtube_transcript_piped(video_id, languages)
    except Exception as exc:
        errors.append(f"Piped API: {exc}")
        if debug:
            print(f"[DEBUG] Piped API failed: {exc}")
    
    # 所有方法失败
    message = "未能获取字幕，请确认视频有字幕"
    if debug:
        message = f"{message}。尝试的方法: {'; '.join(errors)}"
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

    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    client = OpenAI(api_key=api_key, base_url=base_url)
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


def extract_json_block(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def fetch_youtube_metadata(video_id, url):
    headers = get_youtube_headers()
    cookies = {"CONSENT": "YES+cb.20210328-17-p0.en+FX+111"}
    title = ""
    description = ""
    author = ""
    errors = []

    oembed_url = f"https://www.youtube.com/oembed?url={quote(url)}&format=json"
    try:
        response = requests.get(oembed_url, headers=headers, timeout=10)
        if response.ok:
            data = response.json()
            title = data.get("title", "") or title
            author = data.get("author_name", "") or author
        else:
            errors.append(RuntimeError(f"{oembed_url} -> {response.status_code}"))
    except Exception as exc:
        errors.append(exc)

    if not title or not description:
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            response = requests.get(watch_url, headers=headers, cookies=cookies, timeout=10)
            if response.ok:
                payload = extract_json_object(response.text, "ytInitialPlayerResponse")
                if payload:
                    data = json.loads(payload)
                    details = data.get("videoDetails", {})
                    title = details.get("title", "") or title
                    description = details.get("shortDescription", "") or description
                    author = details.get("author", "") or author
            else:
                errors.append(RuntimeError(f"{watch_url} -> {response.status_code}"))
        except Exception as exc:
            errors.append(exc)

    if not title and not description:
        raise RuntimeError(f"metadata unavailable: {errors}")

    return {
        "title": title.strip(),
        "description": description.strip(),
        "author": author.strip(),
    }


def build_metadata_text(metadata):
    parts = []
    title = metadata.get("title")
    description = metadata.get("description")
    author = metadata.get("author")
    if title:
        parts.append(f"标题：{title}")
    if description:
        parts.append(f"描述：{description}")
    if author:
        parts.append(f"作者：{author}")
    return "\n".join(parts).strip()


def classify_youtube_error(*errors):
    text = " ".join([str(err) for err in errors if err]).lower()
    if not text:
        return "UNKNOWN"
    if "not a bot" in text or "sign in" in text or "429" in text:
        return "BOT_BLOCKED"
    if "caption" in text or "subtitle" in text or "transcript" in text or "字幕" in text:
        return "NO_CAPTION"
    if "yt-dlp" in text or "download" in text or "audio" in text:
        return "YTDLP_FAILED"
    if "whisper" in text or "openai" in text:
        return "ASR_FAILED"
    if "timeout" in text or "connection" in text:
        return "NETWORK"
    return "UNKNOWN"


def summarize_with_gemini(text, platform):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
    except Exception:
        return None

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    max_chars = int(os.getenv("SUMMARY_INPUT_CHARS", "12000"))
    snippet = text[:max_chars]

    prompt = (
        "你是内容总结助手，请用中文输出精简摘要，并给出 3 条要点。"
        "返回 JSON 格式：{\"summary\":\"...\",\"highlights\":[{\"label\":\"...\",\"text\":\"...\"}]}"
        "label 要简短。保留原文专有名词。"
        f"\n平台：{platform}\n内容：{snippet}"
    )

    try:
        response = model.generate_content(prompt)
        content = response.text or ""
    except Exception:
        return None

    json_text = extract_json_block(content)
    if not json_text:
        return None

    try:
        data = json.loads(json_text)
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


def build_summary_with_fallback(text, platform):
    llm_summary = summarize_with_gemini(text, platform) or summarize_with_openai(text, platform)
    if llm_summary:
        return llm_summary, True
    cleaned = text.strip()
    if len(cleaned) > 400:
        cleaned = cleaned[:400].rstrip() + "..."
    return {"summary": cleaned, "highlights": []}, False


def build_youtube_summary(text):
    summary, _ = build_summary_with_fallback(text, "YouTube")
    return summary


def build_twitter_summary(text):
    summary = text.strip()
    return {"summary": summary, "highlights": []}


def is_audio_transcription_enabled():
    return os.getenv("ENABLE_AUDIO_TRANSCRIPT", "").lower() in ("1", "true", "yes")


def transcribe_audio_with_openai(file_path):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 OPENAI_API_KEY，无法进行音频转写。")
    try:
        from openai import OpenAI
    except Exception:
        raise RuntimeError("OpenAI SDK 未安装，无法进行音频转写。")
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    client = OpenAI(api_key=api_key, base_url=base_url)
    model = os.getenv("WHISPER_MODEL", "whisper-1")
    with open(file_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="text",
        )
    if isinstance(result, str):
        return result
    return getattr(result, "text", "") or ""


def transcribe_youtube_audio(video_url):
    try:
        from yt_dlp import YoutubeDL
    except Exception:
        raise RuntimeError("yt-dlp 未安装，无法下载视频音频。")

    max_mb = os.getenv("YOUTUBE_AUDIO_MAX_MB")
    max_bytes = None
    if max_mb and max_mb.isdigit():
        max_bytes = int(max_mb) * 1024 * 1024

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_template = os.path.join(tmp_dir, "%(id)s.%(ext)s")
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 10,
        }
        if max_bytes:
            ydl_opts["max_filesize"] = max_bytes
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info)
            if not os.path.exists(file_path):
                file_path = os.path.join(
                    tmp_dir, f"{info.get('id', 'audio')}.{info.get('ext', 'm4a')}"
                )
        if not os.path.exists(file_path):
            raise RuntimeError("下载音频失败，未找到输出文件。")
        transcript = transcribe_audio_with_openai(file_path)
        if not transcript.strip():
            raise RuntimeError("音频转写结果为空。")
        return transcript


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
@app.route('/api/magic', methods=['POST'])
def parse_content():
    data = request.get_json(silent=True) or {}
    url = data.get('url')
    platform = data.get('platform')

    if not url:
        return jsonify({"error": "URL is required"}), 400
    if not platform:
        return jsonify({"error": "Platform is required"}), 400

    cache_key = f"{platform}:{url}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)

    try:
        if platform == 'YouTube':
            video_id = extract_youtube_id(url)
            if not video_id:
                return jsonify({"error": "Invalid YouTube URL"}), 400

            transcript_error = None
            audio_error = None
            metadata_error = None
            full_text = ""
            source = None
            metadata = None

            try:
                transcript_data = fetch_youtube_transcript(video_id)
                full_text = transcript_to_text(transcript_data)
                if full_text:
                    source = "transcript"
            except Exception as exc:
                transcript_error = exc

            if not full_text and is_audio_transcription_enabled():
                try:
                    full_text = transcribe_youtube_audio(url)
                    if full_text:
                        source = "audio"
                except Exception as exc:
                    audio_error = exc

            if not full_text:
                try:
                    metadata = fetch_youtube_metadata(video_id, url)
                    full_text = build_metadata_text(metadata)
                    if full_text:
                        source = "metadata"
                except Exception as exc:
                    metadata_error = exc

            if not full_text:
                category = classify_youtube_error(transcript_error, audio_error, metadata_error)
                message = f"未能获取视频内容（{category}）。"
                if is_debug_enabled():
                    details = []
                    if transcript_error:
                        details.append(f"transcript_error={transcript_error}")
                    if audio_error:
                        details.append(f"audio_error={audio_error}")
                    if metadata_error:
                        details.append(f"metadata_error={metadata_error}")
                    if details:
                        message = f"{message} ({'; '.join(details)})"
                raise RuntimeError(message)

            summary_data, used_llm = build_summary_with_fallback(full_text, "YouTube")
            title = metadata.get("title") if metadata else ""
            title = title or "YouTube 视频内容实时解析 (Real Prototype)"
            if source == "transcript":
                confidence = "100% (Transcript + AI)" if used_llm else "85% (Transcript)"
            elif source == "audio":
                confidence = "90% (Audio + AI)" if used_llm else "70% (Audio)"
            else:
                confidence = "70% (Metadata + AI)" if used_llm else "50% (Metadata)"
            if source == "metadata":
                length = f"{len(full_text)} 字符"
            else:
                length = f"{max(1, len(full_text) // 1000)}k 字符"

            # For this prototype, we return the transcript length and summary
            response_payload = {
                "title": title,
                "summary": summary_data.get("summary", ""),
                "length": length,
                "confidence": confidence,
                "highlights": summary_data.get("highlights", [])
            }
            cache_set(cache_key, response_payload)
            return jsonify(response_payload)

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
            response_payload = {
                "title": title,
                "summary": summary_data.get("summary", ""),
                "length": f"{len(text)} 字符",
                "confidence": confidence,
                "highlights": summary_data.get("highlights", [])
            }
            cache_set(cache_key, response_payload)
            return jsonify(response_payload)

        return jsonify({"error": "Unsupported platform"}), 400

    except Exception as e:
        return jsonify({
            "error": "extraction-failed",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

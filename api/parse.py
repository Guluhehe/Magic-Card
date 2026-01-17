from flask import Flask, jsonify, request

from server import (
    build_twitter_summary,
    build_youtube_summary,
    extract_youtube_id,
    fetch_twitter_text,
    parse_cookie_header,
)

app = Flask(__name__)


@app.route("/", methods=["POST"])
def handler():
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    platform = data.get("platform")

    if not url:
        return jsonify({"error": "URL is required"}), 400
    if not platform:
        return jsonify({"error": "Platform is required"}), 400

    try:
        if platform == "YouTube":
            video_id = extract_youtube_id(url)
            if not video_id:
                return jsonify({"error": "Invalid YouTube URL"}), 400

            from server import YouTubeTranscriptApi

            try:
                if hasattr(YouTubeTranscriptApi, "get_transcript"):
                    transcript_data = YouTubeTranscriptApi.get_transcript(
                        video_id,
                        languages=["zh-CN", "en"],
                    )
                else:
                    raise AttributeError("get_transcript not available")
            except Exception:
                if hasattr(YouTubeTranscriptApi, "list_transcripts"):
                    transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                else:
                    transcripts = YouTubeTranscriptApi().list(video_id)
                transcript = transcripts.find_transcript(["zh-Hans", "zh-CN", "en"])
                transcript_data = transcript.fetch()

            def extract_text(item):
                if isinstance(item, dict):
                    return item.get("text", "")
                if hasattr(item, "text"):
                    return item.text
                return ""

            full_text = " ".join(
                [extract_text(item) for item in transcript_data if extract_text(item)]
            )
            summary_data = build_youtube_summary(full_text)

            return jsonify(
                {
                    "title": "YouTube 视频内容实时解析 (Real Prototype)",
                    "summary": summary_data.get("summary", ""),
                    "length": f"{len(full_text) // 1000}k 字符",
                    "confidence": "100% (Direct Extraction)",
                    "highlights": summary_data.get("highlights", []),
                }
            )

        if platform == "Twitter":
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
            highlights = list(summary_data.get("highlights", []))
            highlights.append({"label": "抓取方式", "text": method_label})

            return jsonify(
                {
                    "title": title,
                    "summary": summary_data.get("summary", ""),
                    "length": f"{len(text)} 字符",
                    "confidence": confidence,
                    "highlights": highlights,
                }
            )

        return jsonify({"error": "Unsupported platform"}), 400

    except Exception as exc:
        return (
            jsonify({"error": "extraction-failed", "message": str(exc)}),
            500,
        )

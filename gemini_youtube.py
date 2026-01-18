"""
Gemini YouTube 视频总结模块
使用 Google Gemini API 直接处理 YouTube 视频，无需下载字幕
"""
import os
import google.generativeai as genai


def summarize_youtube_with_gemini(video_url, video_id):
    """
    使用 Gemini API 直接总结 YouTube 视频
    无需下载字幕，Gemini 会自动提取视频内容
    
    Args:
        video_url: 完整的 YouTube URL
        video_id: YouTube 视频 ID
    
    Returns:
        dict: {
            "summary": "中文摘要",
            "highlights": [{"label": "...", "text": "..."}, ...]
        }
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 GEMINI_API_KEY，无法使用 Gemini 视频总结功能")
    
    # 配置 Gemini
    genai.configure(api_key=api_key)
    
    # 使用 Gemini 1.5 Flash（更快更便宜）或 1.5 Pro（更强大）
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    
    # 提示词
    prompt = f"""
请分析这个 YouTube 视频并生成中文总结：

视频链接：{video_url}

请提供：
1. **核心观点**：用 2-3 句话概括视频的主要内容
2. **关键亮点**：列出 3-5 个最重要的要点
3. **适用场景**：这个视频适合哪些人观看？

请用中文回答，格式如下：

【核心观点】
...

【关键亮点】
1. ...
2. ...
3. ...

【适用场景】
...
"""
    
    try:
        # 发送请求（Gemini 会自动处理 YouTube URL）
        response = model.generate_content([prompt, video_url])
        
        # 解析响应
        full_text = response.text
        
        # 提取各部分
        summary = extract_section(full_text, "【核心观点】")
        highlights_text = extract_section(full_text, "【关键亮点】")
        scenario_text = extract_section(full_text, "【适用场景】")
        
        # 构建亮点列表
        highlights = []
        
        if highlights_text:
            # 解析亮点列表
            for line in highlights_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith(('-', '•', '·'))):
                    # 移除序号
                    text = re.sub(r'^[\d\-•·.\s]+', '', line).strip()
                    if text:
                        highlights.append({
                            "label": "要点",
                            "text": text
                        })
        
        if scenario_text:
            highlights.append({
                "label": "适用场景",
                "text": scenario_text.strip()
            })
        
        return {
            "summary": summary.strip() if summary else full_text[:200],
            "highlights": highlights[:5]  # 最多 5 个
        }
        
    except Exception as e:
        raise RuntimeError(f"Gemini API 调用失败: {str(e)}")


def extract_section(text, marker):
    """从文本中提取指定章节"""
    if marker not in text:
        return ""
    
    start = text.find(marker) + len(marker)
    
    # 找到下一个【】标记或文本结尾
    next_marker = text.find("【", start)
    if next_marker == -1:
        return text[start:].strip()
    else:
        return text[start:next_marker].strip()


def build_youtube_summary_gemini(video_url, video_id):
    """
    使用 Gemini 构建 YouTube 摘要（fallback 到字幕方式）
    
    Args:
        video_url: YouTube URL
        video_id: YouTube 视频 ID
    
    Returns:
        dict: 摘要数据
    """
    # 优先尝试 Gemini（如果配置了 API Key）
    if os.getenv("GEMINI_API_KEY"):
        try:
            return summarize_youtube_with_gemini(video_url, video_id)
        except Exception as e:
            print(f"[Gemini] 失败，回退到字幕方式: {e}")
    
    # 回退到原有的字幕+OpenAI方式
    from server import fetch_youtube_transcript, transcript_to_text, build_youtube_summary
    
    transcript_data = fetch_youtube_transcript(video_id)
    full_text = transcript_to_text(transcript_data)
    return build_youtube_summary(full_text)

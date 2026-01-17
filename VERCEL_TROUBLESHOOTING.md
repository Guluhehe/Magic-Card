# Vercel 部署诊断与优化指南

## 🔍 问题诊断

### 现象
- ✅ Twitter 链接基本能通
- ❌ YouTube 视频解析失败（字幕获取阶段就出错）

### 可能原因

#### 1. **Serverless 函数超时** ⏱️
**最可能的原因**

Vercel Serverless 函数限制：
- 免费版：**10 秒超时**
- Pro 版：60 秒超时

当前代码的字幕获取策略：
```python
fetch_youtube_transcript(video_id)
  ├── youtube-transcript-api (尝试 1)
  ├── fetch_youtube_transcript_player (尝试 2)
  ├── fetch_youtube_transcript_timedtext (尝试 3)
  ├── fetch_youtube_transcript_piped (尝试 4，遍历 5 个实例)
  └── fetch_youtube_transcript_lemnos (尝试 5)
```

**问题**：
- 如果前几个方法全部失败，会串行尝试所有方法
- Piped 方法会遍历 5 个实例，每个超时 10 秒
- 总耗时可能超过 **50+ 秒**，远超 Vercel 限制

#### 2. **网络请求被阻止** 🚫

Vercel 的出口 IP 可能被 YouTube 识别并限流：
- YouTube timedtext API 可能阻止数据中心 IP
- Piped 实例可能不稳定
- 大量并发请求触发反爬

#### 3. **依赖版本问题** 📦

`youtube-transcript-api` 库可能在 Vercel 环境中表现不同。

## 🛠️ 解决方案

### 方案 A：优化超时策略（推荐）

修改 `server.py`，为 Vercel 环境设置更激进的超时：

```python
def get_request_timeout():
    """Vercel 环境使用更短的超时"""
    is_vercel = os.getenv("VERCEL", "") == "1"
    return 2 if is_vercel else 10

# 在所有 requests.get() 中使用
response = requests.get(url, timeout=get_request_timeout())
```

### 方案 B：使用更快的抓取方法

优先使用最快的方法，跳过慢速备用方案：

```python
def fetch_youtube_transcript_fast(video_id):
    """Vercel 专用：只使用最快的方法"""
    languages = get_preferred_transcript_languages()
    
    # 方法 1: youtube-transcript-api (最快)
    try:
        return YouTubeTranscriptApi.get_transcript(
            video_id, languages=languages
        )
    except:
        pass
    
    # 方法 2: Player API (快速)
    try:
        return fetch_youtube_transcript_player(video_id, languages)
    except:
        pass
    
    # 方法 3: Lemnos (通常比 Piped 快)
    try:
        return fetch_youtube_transcript_lemnos(video_id, languages)
    except:
        pass
    
    # 放弃慢速方法
    raise RuntimeError("字幕获取失败（已跳过慢速备用方案）")
```

### 方案 C：增加并发超时 ⚡（最推荐）

使用 `concurrent.futures` 并行尝试，哪个先成功用哪个：

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

def fetch_youtube_transcript_parallel(video_id):
    languages = get_preferred_transcript_languages()
    
    def try_official():
        return YouTubeTranscriptApi.get_transcript(
            video_id, languages=languages
        )
    
    def try_player():
        return fetch_youtube_transcript_player(video_id, languages)
    
    def try_lemnos():
        return fetch_youtube_transcript_lemnos(video_id, languages)
    
    tasks = [try_official, try_player, try_lemnos]
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(task) for task in tasks]
        
        # 等待任何一个成功，最多等 5 秒
        for future in futures:
            try:
                result = future.result(timeout=5)
                if result:
                    # 取消其他任务
                    for f in futures:
                        f.cancel()
                    return result
            except:
                continue
    
    raise RuntimeError("所有字幕获取方法均失败")
```

### 方案 D：使用环境变量控制

在 Vercel 环境变量中设置：

```env
# 跳过慢速方法
SKIP_SLOW_TRANSCRIPT_METHODS=1

# 只使用官方 API
TRANSCRIPT_METHOD=official_only

# 减少 Piped 实例数量
PIPED_INSTANCES=https://piped.video
```

## 📊 推荐配置

### 1. 立即修复（最快）

在 `server.py` 的 `fetch_youtube_transcript` 函数顶部添加：

```python
def fetch_youtube_transcript(video_id):
    # Vercel 环境：跳过慢速方法
    if os.getenv("VERCEL") == "1" or os.getenv("SKIP_PIPED") == "1":
        languages = get_preferred_transcript_languages()
        
        # 只尝试前 3 个最快的方法
        try:
            return YouTubeTranscriptApi.get_transcript(
                video_id, languages=languages
            )
        except:
            pass
        
        try:
            return fetch_youtube_transcript_player(video_id, languages)
        except:
            pass
        
        try:
            return fetch_youtube_transcript_lemnos(video_id, languages)
        except:
            pass
        
        raise RuntimeError("字幕获取失败")
    
    # 原有的完整逻辑（本地环境）
    # ...
```

### 2. Vercel 环境变量配置

在 Vercel Dashboard → Settings → Environment Variables 中添加：

```
SKIP_PIPED=1
TRANSCRIPT_DEBUG=0
```

### 3. 增加 Vercel 配置

创建 `vercel.json`：

```json
{
  "functions": {
    "api/**/*.py": {
      "maxDuration": 60
    }
  }
}
```

**注意**：`maxDuration: 60` 需要 Pro 计划。免费版固定 10 秒。

## 🔬 调试步骤

1. **启用调试日志**

在 Vercel 环境变量中添加：
```
TRANSCRIPT_DEBUG=1
```

2. **查看 Vercel 日志**

在 Vercel Dashboard → Deployments → [你的部署] → Functions 查看实时日志

3. **本地模拟 Vercel 环境**

```bash
export VERCEL=1
export SKIP_PIPED=1
python3 server.py
```

然后测试：
```bash
curl -X POST http://127.0.0.1:5000/api/parse \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw","platform":"YouTube"}'
```

## 📝 测试清单

- [ ] 本地测试通过（Vercel 模式）
- [ ] 设置 `SKIP_PIPED=1` 环境变量
- [ ] 验证字幕获取在 5 秒内完成
- [ ] 部署到 Vercel
- [ ] 检查 Vercel 函数日志
- [ ] 测试实际视频链接

---

**快速修复建议**：立即在 Vercel 添加环境变量 `SKIP_PIPED=1`，并修改代码检测该变量以跳过慢速方法。

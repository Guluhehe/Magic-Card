# 🚀 MagicCard 部署说明

本项目包含前端页面与后端抓取/总结 API。**OpenAI Key 只能放在后端环境变量里**，不能写进代码或前端。

---

## ✅ 推荐方式：Vercel 前端 + Railway 后端

Vercel 只部署静态前端，后端 API 部署在 Railway，稳定性更高。

### Railway 部署步骤
1. Railway 新建项目 → Deploy from GitHub
2. 选择本仓库，Railway 会自动识别 Python
3. 在 Variables 中配置环境变量（参考 `.env.example`）
   - 必填：`OPENAI_API_KEY`
   - 可选：`TRANSCRIPT_DEBUG`、`TRANSCRIPT_LANGS`、`PIPED_INSTANCES`
4. Start Command 使用 `Procfile` 默认值即可（`gunicorn server:app --bind 0.0.0.0:$PORT`）
5. 在 Settings → Domains 生成域名，得到 `https://xxx.up.railway.app`

### 前端指向 Railway
把 Railway 域名写入 `index.html` 的 `magiccard-api-base`：

```html
<meta name="magiccard-api-base" content="https://xxx.up.railway.app" />
```

提交后重新部署 Vercel。

---

## ✅ 备用方式：Vercel 同域 API

前端请求同域 `/api/parse`，由 `api/parse.py` 提供（Vercel Serverless Function）。

### Vercel 环境变量
在 Vercel Dashboard → Project → Settings → Environment Variables 中配置服务端环境变量。
变量命名可参考 `.env.example`，安全注意事项见 [SECURITY.md](SECURITY.md)。

必填：
- `OPENAI_API_KEY`

可选：
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OPENAI_MODEL`
- `SUMMARY_INPUT_CHARS`
- `ENABLE_AUDIO_TRANSCRIPT=1`（启用音频转写兜底）
- `WHISPER_MODEL`（默认 `whisper-1`）
- `YOUTUBE_AUDIO_MAX_MB`（限制下载体积，比如 `50`）
- `ENABLE_SUBTITLE_DLP=1`（启用 yt-dlp 字幕增强）
- `YOUTUBE_DLP_CLIENTS=android,web`
- `YOUTUBE_PROXY`
- `YOUTUBE_COOKIES_B64`

配置后重新部署一次。

### 部署步骤（Vercel）
1. Vercel Dashboard → New Project → 导入 GitHub 仓库
2. Framework 选择 `Other`
3. Build Command / Output Directory 留空
4. 添加环境变量后点击 Deploy

---

## 🔐 Key 安全原则

- Key 只放在后端环境变量
- 前端不要出现 `OPENAI_API_KEY`
- 不要把 `.env` 提交到 GitHub

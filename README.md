# 🪄 Magic Card - AI 社交媒体内容摘要生成器

> 将 YouTube 视频和 Twitter/X 推文一键转换为精美的 AI 总结卡片

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/AI-OpenAI%20GPT-412991.svg)](https://openai.com/)

![Magic Card Preview](https://via.placeholder.com/800x400/6366f1/ffffff?text=Magic+Card+Preview)

## ✨ 核心特性

- 🎬 **YouTube 视频总结**：自动提取字幕并用 AI 生成精炼摘要
- 🐦 **Twitter/X 推文抓取**：多级降级策略，最大化成功率
- 🤖 **GPT-4o-mini 智能总结**：结构化输出（摘要 + 3 个核心要点）
- 🎨 **Glassmorphism UI**：现代化玻璃拟态设计 + 平滑动画
- 📥 **一键下载卡片**：生成的内容卡片可导出为 PNG 图片
- 🌐 **智能环境适配**：同一套代码支持本地开发和云端部署

## 🚀 快速开始

### 前置要求

- **Python 3.9+**
- **Node.js 14+**（可选，仅需前端独立运行时）
- **OpenAI API Key**（用于 AI 总结功能）

### 1. 克隆项目

```bash
git clone https://github.com/Guluhehe/Magic-Card.git
cd Magic-Card
```

### 2. 安装后端依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（重要！🔒）

**⚠️ 安全警告**：永远不要将 API Key 提交到 Git！详见 [SECURITY.md](SECURITY.md)

**方法 A：使用 .env 文件（推荐）**

```bash
# 1. 复制模板
cp .env.example .env

# 2. 编辑 .env 文件，填入你的真实 API Key
nano .env
```

在 `.env` 中填写：
```env
OPENAI_API_KEY=sk-proj-your-actual-key-here
OPENAI_MODEL=gpt-4o-mini
```

**方法 B：直接导出环境变量**

```bash
export OPENAI_API_KEY="sk-proj-your-actual-key-here"
export OPENAI_MODEL="gpt-4o-mini"
```

**获取 OpenAI API Key**：
1. 访问 https://platform.openai.com/api-keys
2. 创建新密钥
3. 复制密钥（只显示一次）
4. **设置使用限额**防止意外消费

### 4. 启动后端服务

```bash
python3 server.py
```

服务将运行在：`http://127.0.0.1:5000`

### 5. 打开前端

**方法 A：直接打开 HTML**

```bash
open index.html  # macOS
# 或直接双击 index.html 文件
```

**方法 B：使用简单 HTTP 服务器**

```bash
python3 -m http.server 3000
# 访问 http://localhost:3000
```

## 📖 使用指南

### 基本使用流程

1. **输入链接**：在输入框中粘贴 YouTube 或 Twitter/X 链接
2. **点击生成**：等待 AI 处理（通常 5-15 秒）
3. **查看卡片**：自动滚动到生成的精美卡片
4. **自定义样式**（可选）：调整卡片颜色、密度、是否显示要点
5. **下载卡片**：点击 Download 按钮导出为 PNG 图片

### 支持的链接格式

#### YouTube

```
✅ https://www.youtube.com/watch?v=VIDEO_ID
✅ https://youtu.be/VIDEO_ID
✅ https://www.youtube.com/shorts/VIDEO_ID
✅ https://m.youtube.com/watch?v=VIDEO_ID
```

#### Twitter / X

```
✅ https://twitter.com/username/status/TWEET_ID
✅ https://x.com/username/status/TWEET_ID
```

## 🏗️ 架构设计

```
┌─────────────────┐      HTTP POST       ┌──────────────────┐
│                 │ ──────────────────▶  │                  │
│  Frontend (SPA) │                      │  Flask Backend   │
│  - index.html   │ ◀──────────────────  │  - server.py     │
│  - script.js    │      JSON Response   │                  │
│  - styles.css   │                      │                  │
└─────────────────┘                      └──────────────────┘
                                                  │
                                                  ▼
                        ┌────────────────────────────────────┐
                        │  Content Extraction Layer          │
                        ├────────────────────────────────────┤
                        │  YouTube: youtube-transcript-api   │
                        │  Twitter: FixTweet → Syndication   │
                        │           → snscrape → Playwright  │
                        └────────────────────────────────────┘
                                                  │
                                                  ▼
                        ┌────────────────────────────────────┐
                        │  AI Summarization (OpenAI GPT)     │
                        │  - Structured JSON Output          │
                        │  - 中文摘要 + 3 个要点              │
                        └────────────────────────────────────┘
```

## 🔧 技术栈

### 前端

- **核心**：原生 JavaScript (ES6+)
- **样式**：Vanilla CSS (Glassmorphism + 动画)
- **字体**：Google Fonts (Outfit, Inter)
- **截图**：html2canvas.js

### 后端

- **框架**：Flask + Flask-CORS
- **YouTube 抓取**：youtube-transcript-api
- **Twitter 抓取**：
  - FixTweet API（主要）
  - Syndication API（降级）
  - snscrape（可选）
  - Playwright（兜底，需额外安装）
- **AI 总结**：OpenAI Python SDK

## 🎨 UI 特性

### Glassmorphism 玻璃拟态

- 半透明背景 + 高斯模糊
- 微妙的边框和阴影
- 丝滑的 hover 动画

### 响应式交互

- 结果面板按需显示（生成前隐藏）
- 自动平滑滚动到卡片位置
- 实时样式预览

### 卡片下载

- html2canvas 高质量渲染
- 2x DPI 输出（适配高清屏）
- 下载时自动隐藏按钮

## 📝 API 端点

### POST `/api/parse`

**请求体：**

```json
{
  "url": "https://www.youtube.com/watch?v=xxxx",
  "platform": "YouTube"
}
```

**响应（成功）：**

```json
{
  "title": "视频标题或推文作者",
  "summary": "AI 生成的中文摘要...",
  "length": "3k 字符",
  "confidence": "100% (Direct Extraction)",
  "highlights": [
    { "label": "核心观点", "text": "..." },
    { "label": "关键数据", "text": "..." },
    { "label": "应用场景", "text": "..." }
  ]
}
```

**响应（失败）：**

```json
{
  "error": "extraction-failed",
  "message": "详细错误信息"
}
```

## ⚠️ 已知限制

### YouTube

- ✅ **字幕可用性**：只能抓取有字幕的视频（自动生成或人工添加）
- ✅ **语言支持**：优先中文，降级至英文
- ❌ **无字幕视频**：无法处理

### Twitter / X

- ⚠️ **反爬限制**：X/Twitter 在 2024 年后加强了反爬虫措施
- ✅ **多级降级**：使用 4 种方法提高成功率
- ❌ **私密推文**：无法访问受保护的账号
- ❌ **需要登录的推文**：可能失败（除非提供 Cookie）

### AI 总结

- 💰 **费用**：需要 OpenAI API Key（按 Token 计费）
- ⏱️ **速度**：取决于 OpenAI 响应速度（通常 3-10 秒）
- 📏 **输入限制**：默认最多处理 12000 字符（可配置）

## 🚀 部署指南

### 本地开发

已在上文"快速开始"中说明。

### 云端部署（推荐）

#### 前端：Vercel / Netlify

```bash
# 部署前端静态文件
vercel deploy
```

**环境变量（Vercel）**：无需配置（前端调用同域后端）

#### 后端：Railway / Render

1. 在平台上创建新项目
2. 链接 GitHub 仓库
3. 设置环境变量：
   ```
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```
4. 部署 `server.py`

**注意**：如果前后端分离部署，需修改 `script.js` 中的 `getApiBase()` 返回后端 URL。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交改动：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

### 代码规范

- Python：PEP 8
- JavaScript：ESLint (Airbnb Style)
- Commits：Conventional Commits

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [OpenAI](https://openai.com/) - GPT API
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - YouTube 字幕抓取
- [FixTweet](https://github.com/FixTweet/FixTweet) - Twitter 内容提取
- [html2canvas](https://html2canvas.hertzen.com/) - HTML 转图片

## 📬 联系方式

- **项目主页**：[https://github.com/Guluhehe/Magic-Card](https://github.com/Guluhehe/Magic-Card)
- **Issue 反馈**：[GitHub Issues](https://github.com/Guluhehe/Magic-Card/issues)

---

**Made with ❤️ by [Guluhehe](https://github.com/Guluhehe)**

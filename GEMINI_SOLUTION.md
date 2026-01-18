# Magic Card - Gemini YouTube 方案

## 🎉 好消息！解决 YouTube 字幕限制

### 问题回顾

YouTube 限制了数据中心 IP 访问字幕 API，导致：
- ❌ Vercel / Render 等云平台无法下载字幕
- ❌ 所有字幕 API（Player、TimedText、Piped）都返回空

### ✨ 新方案：Gemini API

Google Gemini 1.5 有一个独特功能：

**可以直接处理 YouTube 视频 URL，无需下载字幕！**

#### 工作原理

```
YouTube URL → Gemini API → 视频理解 → 中文摘要
```

Gemini 会：
1. 自动提取视频的视觉和音频内容
2. 理解完整的视频上下文
3. 生成准确的摘要

**完全绕过字幕下载限制！** 🚀

---

## 📋 配置步骤

### 1. 获取 Gemini API Key

访问：https://aistudio.google.com/app/apikey

1. 登录 Google 账号
2. 点击 **"Create API Key"**
3. 复制密钥（格式：`AIzaSy...`）

### 2. 在 Render 中配置环境变量

进入 Render Dashboard → Magic-Card 服务 → Environment

添加新变量：

```
GEMINI_API_KEY = AIzaSy你的密钥
GEMINI_MODEL = gemini-1.5-flash
```

**可选模型**：
- `gemini-1.5-flash`（推荐）：更快、更便宜
- `gemini-1.5-pro`：更强大、更准确

### 3. 更新代码

已创建 `gemini_youtube.py` 模块，需要集成到 `server.py`

### 4. 部署

```bash
git add .
git commit -m "feat: Add Gemini YouTube video understanding"
git push
```

Render 会自动重新部署。

---

## 💰 费用对比

### Gemini API（推荐）

| 模型 | 免费额度 | 付费价格 |
|------|---------|---------|
| **Gemini 1.5 Flash** | 15 RPM, 100万 tokens/天 | $0.075 / 100万 tokens (输入) |
| **Gemini 1.5 Pro** | 2 RPM, 3.2万 tokens/天 | $1.25 / 100万 tokens (输入) |

**单次视频总结成本**：
- Flash：约 $0.0001（0.01 分）
- Pro：约 $0.002（0.2 分）

### OpenAI GPT-4o-mini（字幕方式）

| 操作 | 成本 |
|------|------|
| 单次总结 | 约 $0.0003（0.03 分）|

**结论**：Gemini Flash 更便宜且无需字幕！

---

## ✅ 优势

### vs 字幕下载方式

| 特性 | 字幕方式 | Gemini 方式 |
|------|---------|------------|
| 云部署 | ❌ 被限制 | ✅ 完全可用 |
| 理解能力 | ⚠️ 仅文本 | ✅ 视觉+音频 |
| 准确性 | ⚠️ 依赖字幕质量 | ✅ 直接理解内容 |
| 速度 | 快（如果能获取） | 中等（需处理视频）|
| 成本 | OpenAI 费用 | Gemini 费用（更低）|

---

## 🎯 实现计划

### Phase 1：创建 Gemini 模块 ✅

已完成：`gemini_youtube.py`

### Phase 2：集成到 server.py

修改 `/api/parse` 端点，优先使用 Gemini

### Phase 3：测试

1. 配置 `GEMINI_API_KEY`
2. 重新部署
3. 测试 YouTube 视频

### Phase 4：文档更新

更新 README，说明新的 YouTube 处理方式

---

## 🔄 降级策略

```python
if GEMINI_API_KEY 存在:
    try:
        使用 Gemini 处理视频
    except:
        回退到字幕方式（本地可用）
else:
    使用字幕方式
```

这样：
- ✅ 云部署：自动使用 Gemini
- ✅ 本地开发：可选 Gemini 或字幕
- ✅ 向后兼容：不影响现有功能

---

## 📝 待办事项

- [ ] 获取 Gemini API Key
- [ ] 在 Render 配置环境变量
- [ ] 修改 `server.py` 集成 Gemini
- [ ] 测试 YouTube 视频总结
- [ ] 更新文档

---

## 🚀 预期效果

配置完成后：

**输入**：`https://www.youtube.com/watch?v=dQw4w9WgXcQ`

**输出**：
```json
{
  "title": "YouTube 视频内容实时解析",
  "summary": "这是一首 1987 年发布的经典流行歌曲...",
  "highlights": [
    {"label": "要点", "text": "音乐风格：80 年代流行"},
    {"label": "要点", "text": "文化影响：成为互联网 meme"},
    {"label": "适用场景", "text": "适合对流行音乐文化感兴趣的观众"}
  ]
}
```

**完全可用！** ✅

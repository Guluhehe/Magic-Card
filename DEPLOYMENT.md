# 🚀 MagicCard 部署说明（Vercel）

本项目包含前端页面与后端抓取/总结 API。**OpenAI Key 只能放在后端环境变量里**，不能写进代码或前端。

---

## ✅ 推荐方式：Vercel 同域 API

前端会请求同域 `/api/parse`。因此线上需要有一个可用的 API 路由。

> 说明：当前仓库后端是 Flask（`server.py`），Vercel 不支持常驻 Flask 服务。
> 若要在 Vercel 同域提供 API，需要改成 Serverless Function（如 `api/parse.py`）。
> 需要我帮你把 Flask 迁移为 Vercel API，请直接说。

### 设置环境变量
在 Vercel Dashboard → Project → Settings → Environment Variables 中配置服务端环境变量。
变量命名可参考 `.env.example`，安全注意事项见 [SECURITY.md](SECURITY.md)。

必填：
- `OPENAI_API_KEY`

可选：
- `OPENAI_MODEL`
- `SUMMARY_INPUT_CHARS`

配置后重新部署一次。

---

## ✅ 备用方式：Vercel 前端 + 独立后端

如果你把 Flask 部署到 Render/Fly/自建服务器：

1. 保证后端可访问 `/api/parse`
2. 修改 `script.js` 里的 `getApiBase()`，让线上指向你的后端域名
3. 重新部署前端

---

## 🔐 Key 安全原则

- Key 只放在后端环境变量
- 前端不要出现 `OPENAI_API_KEY`
- 不要把 `.env` 提交到 GitHub

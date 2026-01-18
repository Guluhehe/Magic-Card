# ⚙️ Vercel 环境变量配置指南

**最后更新**: 2026-01-18 18:15  
**紧急**: 修复 OpenAI 客户端兼容性问题

---

## 🔧 必需的 Vercel 环境变量

请在 **Vercel Dashboard** → **你的项目** → **Settings** → **Environment Variables** 设置：

### 1. OpenAI API Key（必需）
```
Name:  OPENAI_API_KEY
Value: 你的 openkey.cloud API 密钥
```

### 2. OpenAI Base URL（必需 - 用于 openkey.cloud）
```
Name:  OPENAI_BASE_URL  
Value: https://openkey.cloud/v1
```

### 3. OpenAI Model（可选）
```
Name:  OPENAI_MODEL
Value: gpt-4o-mini
```
（如果不设置，默认使用 gpt-4o-mini）

---

## 🚨 重要提示

### ⚠️ 设置环境变量后必须做的事：

1. **保存环境变量后**
2. **前往 Deployments 标签**
3. **点击最新部署旁的 "..." 按钮**
4. **选择 "Redeploy"**
5. **勾选掉 "Use existing Build Cache"（清除缓存）**
6. **点击 "Redeploy"**

**环境变量更新后不会自动生效，必须手动 Redeploy！**

---

## ✅ 验证配置

### 方法 1: 检查部署日志
1. 进入 Vercel Dashboard
2. 点击最新的 Deployment
3. 查看 Build Logs
4. 确认没有 "OPENAI_API_KEY not found" 错误

### 方法 2: 测试 API
等待部署完成后，运行：

```bash
curl -X POST https://magic-card-rust.vercel.app/api/magic \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw","platform":"YouTube"}'
```

**成功响应示例**:
```json
{
  "title": "YouTube 视频精华 [GPT分析]",
  "summary": "...",
  "highlights": [...]
}
```

**失败响应示例**:
```json
{
  "error": "extraction-failed",
  "message": "未配置 OPENAI_API_KEY"
}
```

---

## 📋 完整配置检查清单

- [ ] `OPENAI_API_KEY` 已设置
- [ ] `OPENAI_BASE_URL` 已设置为 `https://openkey.cloud/v1`
- [ ] 环境变量保存后触发了 **Redeploy**
- [ ] Redeploy 时清除了缓存
- [ ] 等待部署完成（约 1-2 分钟）
- [ ] 使用无痕模式测试网站

---

## 🐛 常见问题

### Q: 我设置了环境变量，为什么还是报错？
**A**: 环境变量更新后必须手动 Redeploy！Vercel 不会自动应用新的环境变量到已有部署。

### Q: "Failed to fetch" 错误
**A**: 
1. 清除浏览器缓存或使用无痕模式
2. 检查 Vercel 部署状态是否成功
3. 确认环境变量已正确设置并 Redeploy

### Q: "Client.__init__() got an unexpected keyword argument"
**A**: 这已在最新代码中修复（commit 34ddccc）。确保：
1. GitHub 已有最新代码
2. Vercel 已自动或手动重新部署

---

## 🎯 下一步

1. ✅ 代码已推送（修复了 OpenAI 客户端初始化问题）
2. ⏱️ **等待 Vercel 自动部署**（约 1-2 分钟）
3. 🔐 **在 Vercel 设置环境变量**（如果还没设置）
4. 🔄 **Redeploy**（如果刚刚更新了环境变量）
5. 🧪 **测试**

---

**部署时间**: 2026-01-18 18:15  
**提交**: 34ddccc  
**状态**: 🟡 等待 Vercel 部署 + 环境变量配置

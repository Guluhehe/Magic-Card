# 🔒 Security Best Practices

## API Key 安全管理

### ⚠️ 重要提醒

**永远不要将 API Key 提交到 Git 仓库！**

- ❌ 不要硬编码 API Key 到代码中
- ❌ 不要将 `.env` 文件提交到 GitHub
- ❌ 不要在公开的 Issue/PR 中粘贴 API Key
- ✅ 使用环境变量存储敏感信息
- ✅ 使用 `.env.example` 作为模板
- ✅ 将 `.env` 添加到 `.gitignore`

## 本地开发配置

### 1. 复制环境变量模板

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

```bash
# 使用你喜欢的编辑器打开
nano .env
# 或
code .env
```

### 3. 填入你的真实 API Key

```env
OPENAI_API_KEY=sk-proj-your-actual-key-here-xxxxx
OPENAI_MODEL=gpt-4o-mini
```

### 4. 确认 .env 已被 .gitignore 忽略

```bash
git status
# 应该看不到 .env 文件
```

## 生产环境部署

### Vercel

在项目设置中添加环境变量：

1. 打开 Vercel 项目面板
2. Settings → Environment Variables
3. 添加：
   - Name: `OPENAI_API_KEY`
   - Value: `sk-proj-...`
   - Environment: Production

### Railway

```bash
railway variables set OPENAI_API_KEY=sk-proj-...
```

### Render

在 Dashboard → Environment 中添加：
- Key: `OPENAI_API_KEY`
- Value: `sk-proj-...`

### Docker

```bash
docker run -e OPENAI_API_KEY=sk-proj-... your-image
```

## API Key 泄露应对

如果不小心泄露了 API Key：

1. **立即撤销**：
   - 访问 https://platform.openai.com/api-keys
   - 删除泄露的 Key
   
2. **生成新 Key**：
   - 创建一个新的 API Key
   - 更新所有使用该 Key 的环境

3. **检查使用记录**：
   - 查看 OpenAI Usage Dashboard
   - 确认是否有异常调用

4. **清理 Git 历史**（如果已提交到 GitHub）：
   ```bash
   # 警告：这会重写历史，慎用！
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   
   git push origin --force --all
   ```

5. **联系 GitHub Support**：
   - 如果是公开仓库，GitHub 可能会自动检测并通知你
   - 可以请求 GitHub 从缓存中删除敏感数据

## 额外安全建议

### 限制 API Key 权限

在 OpenAI 平台创建 Key 时：
- 设置使用限额（例如每月 $10）
- 仅启用必要的权限
- 定期轮换 Key

### 使用 Secret Scanning

启用 GitHub 的 Secret Scanning：
- Settings → Code security and analysis
- 启用 "Secret scanning"

### Rate Limiting

在代码中实现速率限制：
```python
from functools import lru_cache
from time import time

@lru_cache(maxsize=100)
def cached_summary(text_hash):
    # 缓存相同内容的总结
    pass
```

## 检查清单

在部署前确认：

- [ ] `.env` 已添加到 `.gitignore`
- [ ] 没有硬编码的 API Key
- [ ] 生产环境的环境变量已正确配置
- [ ] API Key 设置了使用限额
- [ ] 定期审查 API 使用情况

---

**Remember**: Your API Key is like a password. Treat it with the same level of security!

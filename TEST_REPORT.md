# Magic Card 测试报告

## 测试时间
2026-01-17 21:12

## 环境检测结果

### ✅ Python 环境
- Python 版本: 3.9.6
- Flask: 3.1.2 ✅
- youtube-transcript-api: 已安装 ✅
- OpenAI SDK: 2.15.0 ✅

### ❌ 配置问题
- **OPENAI_API_KEY: 未设置** ⚠️

## 问题诊断

当前项目无法正常运行 AI 总结功能，因为缺少 OpenAI API 密钥。

### 报错示例
```json
{
  "error": "extraction-failed",
  "message": "未配置 OPENAI_API_KEY，YouTube 总结需要 AI Key。"
}
```

## 解决方案

### 方案 A：设置环境变量（推荐）

```bash
# 临时设置（当前终端会话有效）
export OPENAI_API_KEY="sk-your-api-key-here"

# 永久设置（添加到 ~/.zshrc 或 ~/.bashrc）
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 方案 B：使用 .env 文件

1. 创建 `.env` 文件：
```bash
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

2. 修改 `server.py` 加载环境变量：
```python
from dotenv import load_dotenv
load_dotenv()
```

3. 安装 python-dotenv：
```bash
pip install python-dotenv
```

### 方案 C：直接在代码中设置（不推荐，仅测试用）

在 `server.py` 顶部添加：
```python
import os
os.environ['OPENAI_API_KEY'] = 'sk-your-api-key-here'
```

## 获取 OpenAI API Key

1. 访问：https://platform.openai.com/api-keys
2. 登录你的 OpenAI 账号
3. 点击 "Create new secret key"
4. 复制密钥（只显示一次，请妥善保存）

### 费用参考（2024年价格）
- **gpt-4o-mini**：$0.150 / 1M input tokens, $0.600 / 1M output tokens
- 平均一次总结消耗：~500 tokens（约 $0.0003，不到1分钱）

## 测试步骤（配置 API Key 后）

### 1. 重启后端服务
```bash
# 如果后端正在运行，先停止（Ctrl+C）
python3 server.py
```

### 2. 测试 YouTube 抓取
```bash
curl -X POST http://127.0.0.1:5000/api/parse \
-H "Content-Type: application/json" \
-d '{
  "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
  "platform": "YouTube"
}'
```

**预期输出**：
```json
{
  "title": "Me at the zoo",
  "summary": "AI 生成的中文摘要...",
  "length": "0k 字符",
  "confidence": "100% (Direct Extraction)",
  "highlights": [
    {"label": "核心观点", "text": "..."},
    {"label": "关键数据", "text": "..."},
    {"label": "应用场景", "text": "..."}
  ]
}
```

### 3. 测试 Twitter 抓取
```bash
curl -X POST http://127.0.0.1:5000/api/parse \
-H "Content-Type: application/json" \
-d '{
  "url": "https://x.com/elonmusk/status/1735910517002899878",
  "platform": "Twitter"
}'
```

### 4. 前端测试
1. 打开 `index.html`
2. 粘贴 YouTube 或 Twitter 链接
3. 点击"生成卡片"
4. 等待 AI 处理（5-15秒）
5. 查看生成的卡片
6. 点击 Download 按钮测试图片导出

## 测试检查清单

- [ ] OpenAI API Key 已配置
- [ ] 后端服务正常启动（http://127.0.0.1:5000）
- [ ] YouTube 抓取正常
- [ ] AI 总结功能正常
- [ ] 前端页面可访问
- [ ] 卡片样式正确显示
- [ ] Download 按钮工作正常
- [ ] Twitter 抓取正常（可能失败，正常现象）

## 预期问题

### YouTube 无字幕
**错误**：`No transcripts available`
**解决**：选择有字幕的视频进行测试

### Twitter 抓取失败
**现象**：所有方法都返回 404
**原因**：X/Twitter 加强了反爬限制
**解决**：这是正常现象，等待第三方服务恢复

### API 配额不足
**错误**：`insufficient_quota`
**解决**：检查 OpenAI 账户余额，充值或更换 API Key

## 状态总结

| 组件 | 状态 | 备注 |
|------|------|------|
| Python 环境 | ✅ | 3.9.6 |
| 依赖安装 | ✅ | 所有核心依赖已安装 |
| API Key 配置 | ❌ | **需要设置 OPENAI_API_KEY** |
| 后端服务 | 🟡 | 运行中但缺少配置 |
| 前端页面 | ✅ | 正常 |
| YouTube 功能 | ⏸️ | 待测试（需配置 API Key） |
| Twitter 功能 | ⏸️ | 待测试 |
| AI 总结 | ❌ | 需配置 API Key |
| 卡片下载 | ⏸️ | 待测试 |

---

**下一步**: 请按照"解决方案"配置 OPENAI_API_KEY，然后重新测试。

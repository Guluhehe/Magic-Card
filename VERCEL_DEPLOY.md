# Vercel Deployment Guide for Magic Card

## 问题：Vercel 返回 "A server error" 而不是 JSON

### 原因
Vercel 无法识别 Flask 应用，需要正确的配置文件。

## 解决方案

### 方案 A：使用 Vercel Serverless Functions（推荐）

#### 1. 项目结构
```
Magic-Card/
├── api/
│   └── parse.py       # Vercel API 路由
├── server.py          # Flask 应用（保留）
├── vercel.json        # Vercel 配置
└── requirements.txt
```

#### 2. 文件内容

**`vercel.json`**（项目根目录）：
```json
{
  "version": 2,
  "builds": [
    {
      "src": "server.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "server.py"
    }
  ],
  "env": {
    "VERCEL": "1"
  }
}
```

**`api/parse.py`**（新建文件）：
```python
from server import app

def handler(request):
    return app(request.environ, lambda *args: None)
```

#### 3. 部署步骤

```bash
# 1. 提交新配置
git add vercel.json api/
git commit -m "feat: Add Vercel serverless configuration"
git push

# 2. Vercel 会自动重新部署
```

#### 4. API 端点

部署后，API 地址变为：
```
https://your-domain.vercel.app/api/parse
```

你的前端代码**已经自动适配**（`getApiBase()` 函数会返回空字符串，使用相对路径）。

---

### 方案 B：纯前端部署 + 外部后端

如果 Vercel Python 部署有问题，可以分离部署：

#### 1. 前端部署到 Vercel
- 只部署 `index.html`, `script.js`, `styles.css`
- 无需后端配置

#### 2. 后端部署到 Railway / Render

**Railway**（推荐，免费）：
```bash
# 1. 安装 Railway CLI
npm install -g @railway/cli

# 2. 登录并部署
railway login
railway init
railway up
```

**Render**（免费，但慢）：
1. 连接 GitHub 仓库
2. 选择 "Python" 类型
3. 启动命令：`python server.py`

#### 3. 修改前端 API Base

在 `script.js` 中硬编码后端地址：

```javascript
const getApiBase = () => {
  return "https://your-backend.railway.app";  // 或 Render URL
};
```

---

## 快速修复（立即尝试）

### 选项 1：修改 server.py 以兼容 Vercel

在 `server.py` 最后添加：

```python
# Vercel serverless function handler
if __name__ != '__main__':
    # 在 Vercel 环境中
    from werkzeug.wrappers import Request, Response
    
    @Request.application
    def application(request):
        return app(request.environ, lambda *args: None)
```

### 选项 2：使用 Vercel Functions API

将 `server.py` 重命名为 `api/index.py` 并修改：

```python
# api/index.py
from http.server import BaseHTTPRequestHandler
import json
# ... (导入其他模块)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 解析请求
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        data = json.loads(body)
        
        # 处理逻辑（从 server.py 移植）
        # ...
        
        # 返回 JSON
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
```

---

## 检查部署状态

### Vercel Dashboard 检查清单

1. **Functions** 标签：
   - 看到 `api/parse` 函数了吗？
   - 函数状态是 "Ready" 还是 "Error"？

2. **Build Logs**：
   - 有没有 Python 依赖安装错误？
   - `requirements.txt` 是否成功安装？

3. **Function Logs**（实时）：
   - 发起一个请求
   - 查看详细错误堆栈

### 常见错误

| 错误消息 | 原因 | 解决方案 |
|---------|------|----------|
| "module not found" | 依赖未安装 | 检查 requirements.txt |
| "timeout" | 函数超过 10s | 已修复（快速模式） |
| "A server error" | 配置问题 | 添加 vercel.json |
| "502 Bad Gateway" | 应用启动失败 | 查看 Build Logs |

---

## 推荐行动

**立即执行**：

```bash
cd /Users/minhao/DevWorkspace/MagicCard

# 已创建的文件
ls vercel.json  # 应该存在
ls api/parse.py  # 应该存在

# 提交并推送
git add vercel.json api/
git commit -m "feat: Add Vercel Python serverless config"
git push
```

等待 Vercel 重新部署（约 2 分钟），然后测试。

---

**如果还是失败**，提供：
1. Vercel Build Logs 截图
2. Vercel Function Logs 截图
3. 我会给你一个**纯 Vercel Functions 版本**（不用 Flask）

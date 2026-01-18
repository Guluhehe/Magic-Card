#!/bin/bash
# 直接测试 Vercel API 端点

echo "测试 Vercel /api/parse 端点..."
echo ""

curl -X POST https://magic-card-rust.vercel.app/api/parse \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "platform": "YouTube"
  }' \
  | python3 -m json.tool

echo ""
echo "如果看到 Gemini 相关的错误或成功响应，说明新代码已部署"
echo "如果看到字幕下载错误，说明还在使用旧代码"

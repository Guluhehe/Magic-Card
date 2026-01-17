#!/bin/bash

# CodeX 插件安装脚本
echo "🚀 开始安装 CodeX 相关工具..."

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    echo "📦 正在检查 Homebrew..."
    
    # 检查 Homebrew
    if command -v brew &> /dev/null; then
        echo "✅ 发现 Homebrew，正在安装 Node.js..."
        brew install node
    else
        echo "⚠️  Homebrew 未安装"
        echo "请选择以下方式之一安装 Node.js:"
        echo "1. 安装 Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "2. 从官网下载: https://nodejs.org/"
        exit 1
    fi
else
    echo "✅ Node.js 已安装: $(node -v)"
fi

# 安装 Codex CLI
if command -v npm &> /dev/null; then
    echo "📦 正在安装 Codex CLI..."
    npm install -g @openai/codex
    
    if [ $? -eq 0 ]; then
        echo "✅ Codex CLI 安装成功！"
        echo "📝 请设置 OPENAI_API_KEY 环境变量"
        echo "   在 ~/.zshrc 或 ~/.bashrc 中添加:"
        echo "   export OPENAI_API_KEY=\"your-api-key-here\""
    else
        echo "❌ Codex CLI 安装失败"
    fi
else
    echo "❌ npm 未找到，无法安装 Codex CLI"
fi

echo ""
echo "📋 下一步：在 Cursor 中安装 Codex 扩展"
echo "   1. 按 Cmd+Shift+X 打开扩展面板"
echo "   2. 搜索 'Codex'"
echo "   3. 点击安装"

#!/bin/bash
# Prompt for API key if not in environment
if [ -z "$GEMINI_API_KEY" ]; then
    echo "请输入 Gemini API Key (或按 Ctrl+C 跳过测试):"
    read -s GEMINI_API_KEY
    export GEMINI_API_KEY
fi

python3 test_magic_api.py

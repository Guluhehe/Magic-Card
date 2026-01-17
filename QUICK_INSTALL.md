# 🚀 CodeX 插件快速安装指南

## ⚡ 最快方式：在 Cursor 中安装（2分钟完成）

### 步骤：

1. **打开扩展面板**
   ```
   快捷键：Cmd + Shift + X
   ```

2. **搜索 Codex**
   - 在搜索框输入：`Codex` 或 `OpenAI Codex`
   - 查找官方扩展（通常显示 OpenAI 或相关标识）

3. **点击安装**
   - 找到后点击绿色的 "Install" 按钮
   - 等待安装完成（通常几秒钟）

4. **完成配置**
   - 安装后可能需要登录 OpenAI 账户
   - 或输入 API Key
   - 按照扩展提示完成即可

5. **验证安装**
   - 按 `Cmd + Shift + P` 打开命令面板
   - 输入 "Codex" 查看可用命令
   - 如果看到 Codex 相关命令，说明安装成功！

---

## 📦 可选：安装 Codex CLI 工具

如果需要命令行工具，需要先安装 Node.js：

### 方式一：使用 Homebrew（推荐）

```bash
# 1. 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装 Node.js
brew install node

# 3. 安装 Codex CLI
npm install -g @openai/codex

# 4. 配置 API Key
export OPENAI_API_KEY="your-api-key-here"
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
```

### 方式二：从官网下载 Node.js

1. 访问：https://nodejs.org/
2. 下载 LTS 版本并安装
3. 打开终端运行：
   ```bash
   npm install -g @openai/codex
   ```

---

## ✅ 当前项目状态

- ✅ Python 依赖已安装（flask, openai 等）
- ✅ requirements.txt 已创建
- ✅ 安装脚本已准备（install_codex.sh）

---

## 🎯 推荐操作

**对于大多数用户，只需要在 Cursor 中安装扩展即可！**

CLI 工具是可选的，主要用于命令行场景。

---

## ❓ 遇到问题？

1. **扩展搜索不到？**
   - 确保网络连接正常
   - 尝试搜索 "OpenAI" 或 "AI Assistant"

2. **安装后无法使用？**
   - 检查是否需要登录
   - 确认 API Key 是否正确配置

3. **需要帮助？**
   - 查看 Cursor 官方文档
   - 检查扩展的 GitHub 页面

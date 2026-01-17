# CodeX 插件安装指南

## 方法一：在 Cursor 中安装 Codex 扩展（推荐）

### 步骤：

1. **打开 Cursor 编辑器**

2. **打开扩展面板**
   - 按快捷键：`Cmd + Shift + X` (macOS) 或 `Ctrl + Shift + X` (Windows/Linux)
   - 或点击左侧边栏的扩展图标

3. **搜索 Codex**
   - 在搜索框中输入 "Codex" 或 "OpenAI Codex"
   - 查找官方发布的扩展（通常由 OpenAI 或相关组织发布）

4. **安装扩展**
   - 点击 "Install" 按钮
   - 等待安装完成

5. **配置和登录**
   - 安装完成后，可能需要登录 OpenAI 账户
   - 或配置 API Key
   - 按照扩展提示完成设置

## 方法二：安装 Codex CLI 工具（可选）

如果需要命令行工具，需要先安装 Node.js：

### 安装 Node.js（如果未安装）

**使用 Homebrew（推荐）：**
```bash
brew install node
```

**或从官网下载：**
访问 https://nodejs.org/ 下载并安装 LTS 版本

### 安装 Codex CLI

```bash
npm install -g @openai/codex
```

### 配置 API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

或在 `~/.zshrc` 或 `~/.bashrc` 中添加：
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## 当前项目状态

✅ Python 依赖已安装：
- flask
- flask-cors
- youtube-transcript-api
- requests
- openai

✅ 已创建 `requirements.txt` 文件

## 验证安装

安装完成后，可以在 Cursor 中：
- 使用 `Cmd + Shift + P` 打开命令面板
- 搜索 "Codex" 相关命令
- 测试 Codex 功能

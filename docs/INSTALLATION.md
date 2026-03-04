# 安装指南

> **详细的安装和环境配置说明**

本指南将帮助您完成系统的完整安装和配置。

---

## 目录

- [系统要求](#系统要求)
- [Python 安装](#python-安装)
- [Claude Code CLI 安装](#claude-code-cli-安装)
- [项目安装](#项目安装)
- [Gemini API 配置（可选）](#gemini-api-配置可选)
- [验证安装](#验证安装)
- [卸载说明](#卸载说明)

---

## 系统要求

### 操作系统

| 系统 | 版本要求 | 支持状态 |
|------|----------|----------|
| **macOS** | macOS 11 (Big Sur) 或更高 | ✅ 完全支持 |
| **Linux** | Ubuntu 20.04+, CentOS 8+, Debian 11+ | ✅ 完全支持 |
| **Windows** | Windows 10/11 | ✅ 支持（需 WSL 或 PowerShell） |

### 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| **CPU** | 2 核心 | 4 核心+ |
| **内存** | 4 GB | 8 GB+ |
| **磁盘空间** | 500 MB | 1 GB+ |
| **网络** | 宽带连接 | 宽带连接 |

### 软件依赖

| 软件 | 版本 | 必需/可选 |
|------|------|-----------|
| **Python** | 3.9+ | ✅ 必需 |
| **pip** | 21.0+ | ✅ 必需 |
| **Claude Code CLI** | 最新版 | ✅ 必需（CLI 模式） |
| **Node.js** | 16.0+ | ✅ 必需（用于安装 Claude CLI） |
| **Git** | 2.0+ | ⚠️ 推荐 |

---

## Python 安装

### 检查 Python 版本

```bash
python --version
# 或
python3 --version
```

**要求**: Python 3.9 或更高版本

### macOS

#### 使用 Homebrew（推荐）

```bash
# 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python@3.11
```

#### 使用官方安装包

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 macOS 安装包
3. 运行安装程序

### Linux (Ubuntu/Debian)

```bash
# 更新包列表
sudo apt update

# 安装 Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip

# 验证安装
python3.11 --version
```

### Linux (CentOS/RHEL)

```bash
# 安装 EPEL 仓库
sudo yum install epel-release

# 安装 Python 3.11
sudo yum install python3.11 python3.11-pip

# 验证安装
python3.11 --version
```

### Windows

#### 方法 1：使用 Microsoft Store（推荐）

1. 打开 Microsoft Store
2. 搜索 "Python 3.11"
3. 点击 "获取" 或 "安装"

#### 方法 2：使用官方安装包

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 Windows 安装包
3. 运行安装程序
4. **重要**: 勾选 "Add Python to PATH"

#### 方法 3：使用 WSL（推荐用于开发）

```powershell
# 启用 WSL
wsl --install

# 在 WSL 中安装 Python
sudo apt update
sudo apt install python3.11 python3-pip
```

### Python 包管理器（pip）

确保 pip 已安装并更新：

```bash
# 升级 pip
python -m pip install --upgrade pip

# 验证
pip --version
```

---

## Claude Code CLI 安装

Claude Code CLI 是 CLI 深度模式的核心依赖。

### 前置要求

- Node.js 16.0 或更高版本
- npm 7.0 或更高版本

### 检查 Node.js 版本

```bash
node --version
npm --version
```

### 安装 Node.js

#### macOS/Linux

```bash
# 使用 nvm（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
```

#### Windows

1. 访问 [Node.js 官网](https://nodejs.org/)
2. 下载 LTS 版本安装包
3. 运行安装程序

### 安装 Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
```

### 验证安装

```bash
claude --version
```

### 配置 Claude CLI

首次使用需要登录：

```bash
claude auth login
```

按照提示完成身份验证。

### 验证 CLI 可用性

```bash
# 测试基本命令
claude --help

# 检查登录状态
claude auth whoami
```

---

## 项目安装

### 获取项目代码

#### 使用 Git（推荐）

```bash
git clone https://github.com/buluslan/review-analyzer.git
cd review-analyzer
```

#### 直接下载

1. 访问 [GitHub 仓库](https://github.com/buluslan/review-analyzer)
2. 点击 "Code" → "Download ZIP"
3. 解压到目标目录
4. 进入项目目录

### 创建虚拟环境（推荐）

**为什么要使用虚拟环境？**
- ✅ 隔离项目依赖
- ✅ 避免版本冲突
- ✅ 易于管理和卸载

#### macOS/Linux

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

#### Windows (CMD)

```cmd
python -m venv venv
venv\Scripts\activate
```

#### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**提示**: 激活成功后，命令行前缀会显示 `(venv)`

### 安装项目依赖

```bash
# 确保在项目根目录
cd review-analyzer

# 安装依赖
pip install -r requirements.txt
```

### 依赖包说明

| 包名 | 版本 | 用途 | 必需/可选 |
|------|------|------|-----------|
| `pandas` | 2.0+ | 数据处理和分析 | ✅ 必需 |
| `jinja2` | 3.1+ | HTML 报告模板渲染 | ✅ 必需 |
| `python-dotenv` | 1.0+ | 环境变量管理 | ✅ 必需 |
| `openpyxl` | 3.0+ | Excel 文件读取 | ✅ 必需 |
| `google-generativeai` | 0.3+ | Gemini API 调用 | ⚠️ 可选 |

### 验证依赖安装

```bash
# 检查已安装的包
pip list

# 验证关键包
python -c "import pandas; print(pandas.__version__)"
python -c "import jinja2; print(jinja2.__version__)"
```

---

## Gemini API 配置（可选）

如果您想使用 Gemini 快速模式，需要配置 Gemini API Key。

### 获取 Gemini API Key

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 登录 Google 账号
3. 点击 "Create API Key"
4. 复制生成的 API Key

### 配置方式

#### 方式 1：环境变量（推荐）

**macOS/Linux**:

```bash
# 临时设置（当前会话有效）
export GEMINI_API_KEY="your-api-key-here"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**Windows**:

```cmd
# 临时设置
set GEMINI_API_KEY=your-api-key-here

# 永久设置（系统环境变量）
# 1. 右键 "此电脑" → "属性" → "高级系统设置"
# 2. "环境变量" → "新建" → 用户变量
# 3. 变量名: GEMINI_API_KEY
# 4. 变量值: your-api-key-here
```

#### 方式 2：.env 文件

1. 复制示例文件：

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件：

```bash
# Gemini API Key（可选）
GEMINI_API_KEY=your-api-key-here
```

3. **重要**: 将 `.env` 添加到 `.gitignore`（避免泄露密钥）

#### 方式 3：运行时输入

不进行任何配置，运行时按提示输入：

```bash
python main.py data/reviews.csv --insights-mode 2
# 程序会提示: 请输入 Gemini API Key:
```

### 验证 API Key

```bash
# 运行测试脚本
python scripts/verify_installation.py
```

---

## 验证安装

### 运行验证脚本

```bash
python scripts/verify_installation.py
```

**预期输出**:

```
✅ Python 版本: 3.11.0
✅ pip 版本: 23.1.0
✅ Claude Code CLI: 已安装
✅ 关键依赖包: 已安装
✅ Gemini API: 已配置（或未配置，取决于您）
```

### 运行示例测试

```bash
# 使用示例数据测试
python main.py examples/reviews_sample.csv
```

**预期结果**:
- ✅ 成功加载评论数据
- ✅ AI 打标完成
- ✅ 生成洞察报告
- ✅ 生成 HTML 看板（如果配置了 Gemini）

### 检查输出文件

```bash
# 进入输出目录
cd output/*-评论分析项目-*/

# 查看生成的文件
ls -lh
```

**应该看到**:
- `评论采集及打标数据_*.csv`
- `分析洞察报告_*.md`
- `可视化洞察报告_*.html`（如果使用 Gemini）

---

## 常见安装问题

### 问题 1: Python 版本过低

**错误**:
```
TypeError: 'type' object is not subscriptable
```

**解决**: 升级到 Python 3.9+

### 问题 2: pip 安装失败

**错误**:
```
ERROR: Could not find a version that satisfies the requirement...
```

**解决**:
```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像（中国用户）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 3: Claude CLI 找不到

**错误**:
```
❌ 找不到 Claude Code CLI！请确保已安装 Claude Code
```

**解决**:
```bash
# 重新安装
npm install -g @anthropic-ai/claude-code

# 检查 PATH
echo $PATH

# 手动添加到 PATH（macOS/Linux）
export PATH="$PATH:$HOME/.npm-global/bin"
```

### 问题 4: 虚拟环境激活失败

**Windows PowerShell 错误**:
```
无法加载文件 venv\Scripts\Activate.ps1，因为在此系统上禁止运行脚本
```

**解决**:
```powershell
# 临时允许脚本执行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 然后再次激活
venv\Scripts\Activate.ps1
```

---

## 卸载说明

### 完全卸载

#### 1. 停用虚拟环境

```bash
deactivate
```

#### 2. 删除项目目录

```bash
# macOS/Linux
rm -rf review-analyzer

# Windows
rmdir /s review-analyzer
```

#### 3. 卸载 Claude CLI（可选）

```bash
npm uninstall -g @anthropic-ai/claude-code
```

#### 4. 删除环境变量（可选）

**macOS/Linux**:
```bash
# 编辑 ~/.bashrc 或 ~/.zshrc
# 删除这一行: export GEMINI_API_KEY="..."
```

**Windows**:
1. 系统设置 → 环境变量
2. 删除 `GEMINI_API_KEY` 变量

---

## 下一步

安装完成后，请查看：

- 📖 [快速开始指南](QUICKSTART.md) - 5 分钟上手
- 🚀 [高级用法](ADVANCED_USAGE.md) - 批量处理和高级配置
- 🏗 [架构说明](ARCHITECTURE.md) - 了解系统设计

---

## 获取帮助

如果安装过程中遇到问题：

1. 查看 [故障排除指南](TROUBLESHOOTING.md)
2. 运行诊断脚本：`python scripts/verify_installation.py`
3. 提交 [GitHub Issue](https://github.com/buluslan/ecommerce-review-analyzer/issues)

---

**安装难度**: ⭐⭐☆☆☆（中等）

**预计时间**: 10-15 分钟

**准备好了吗？继续查看 [快速开始指南](QUICKSTART.md)** 🚀

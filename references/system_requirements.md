# 系统要求

## 基本要求

### 操作系统

| 操作系统 | 版本要求 | 支持状态 |
|---------|---------|---------|
| **macOS** | macOS 11 (Big Sur) 或更高版本 | ✅ 完全支持 |
| **Linux** | Ubuntu 20.04+, CentOS 8+, Debian 11+ | ✅ 完全支持 |
| **Windows** | Windows 10 或 Windows 11 | ✅ 完全支持 |

### Python 环境

| 要求 | 版本 | 必需/可选 |
|------|------|----------|
| **Python** | 3.9 或更高版本 | ✅ 必需 |
| **pip** | 最新版本 | ✅ 必需 |

**检查 Python 版本**:
```bash
python3 --version
# 或
python --version
```

---

## 依赖包

### 核心依赖（必需）

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| **pandas** | ≥ 1.3.0 | 数据处理 |
| **jinja2** | ≥ 3.0.0 | HTML 模板渲染 |
| **openpyxl** | ≥ 3.0.0 | Excel 文件读取 |

### Gemini 依赖（可选）

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| **google-genai** | ≥ 0.3.0 | Gemini API 调用 |

**安装依赖**:
```bash
# 安装核心依赖
pip install pandas jinja2 openpyxl

# 安装 Gemini 依赖（可选）
pip install google-genai

# 或一次性安装所有依赖
pip install pandas jinja2 openpyxl google-genai
```

---

## CLI 模式要求

### Claude CLI

如果使用 **CLI 本地模式**，需要安装 Claude CLI：

```bash
npm install -g @anthropic-ai/claude-code
```

**验证安装**:
```bash
claude --version
```

**系统要求**:
- Node.js 14+ 或 npm 6+
- Claude Code 账户
- 网络连接（用于调用 Claude API）

---

## Gemini 模式要求

### Gemini API Key

如果使用 **Gemini 增强模式** 或 **混动模式**，需要：

1. **获取 API Key**:
   - 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
   - 创建新项目或选择现有项目
   - 点击 "Create API Key"
   - 复制 API Key

2. **配置 API Key**:

**方式 1: 环境变量**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

**方式 2: .env 文件**
```bash
# 在项目根目录或工作目录创建 .env 文件
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

**方式 3: 命令行参数**
```bash
python3 main.py "reviews.csv" --gemini-key "your_api_key_here"
```

### 网络要求

使用 Gemini 模式需要：
- 稳定的互联网连接
- 能够访问 Google API 服务
- 防火墙允许 HTTPS 连接

---

## 硬件要求

### 最低配置

| 组件 | 要求 |
|------|------|
| **CPU** | 2 核心或更高 |
| **内存** | 4 GB RAM |
| **磁盘空间** | 500 MB 可用空间 |
| **网络** | 宽带互联网连接（用于 API 调用） |

### 推荐配置

| 组件 | 要求 |
|------|------|
| **CPU** | 4 核心或更高 |
| **内存** | 8 GB RAM |
| **磁盘空间** | 1 GB 可用空间 |
| **网络** | 稳定的宽带连接 |

---

## 浏览器要求（用于查看 HTML 看板）

| 浏览器 | 版本要求 | 支持状态 |
|--------|---------|---------|
| **Chrome** | 90+ | ✅ 完全支持 |
| **Safari** | 14+ | ✅ 完全支持 |
| **Firefox** | 88+ | ✅ 完全支持 |
| **Edge** | 90+ | ✅ 完全支持 |

---

## 环境检查

### 自动环境检查

工具提供环境检查脚本：

```bash
python3 scripts/check_environment.py
```

输出示例：
```
✅ Python 版本: 3.11.0
✅ pandas: 已安装 (2.0.3)
✅ jinja2: 已安装 (3.1.2)
✅ openpyxl: 已安装 (3.1.2)
⚠️  google-genai: 未安装 (Gemini 模式需要)
⚠️  Claude CLI: 未安装 (CLI 模式需要)
```

### 手动环境检查

**检查 Python**:
```bash
python3 --version
```

**检查依赖**:
```bash
python3 -c "import pandas; import jinja2; import openpyxl; print('所有核心依赖已安装')"
```

**检查 Gemini API**:
```bash
python3 -c "import google.generativeai as genai; print('Gemini SDK 已安装')"
```

**检查 Claude CLI**:
```bash
claude --version
```

---

## 常见安装问题

### 问题 1: pip 安装失败

**症状**: `pip install` 报错

**解决方案**:
```bash
# 升级 pip
python3 -m pip install --upgrade pip

# 使用国内镜像源
pip install pandas jinja2 openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 2: Python 版本过低

**症状**: `Python 3.9+ required` 错误

**解决方案**:
- macOS: `brew install python@3.11`
- Ubuntu: `sudo apt-get install python3.11`
- Windows: 从 [python.org](https://www.python.org/downloads/) 下载安装

### 问题 3: Claude CLI 安装失败

**症状**: `claude not found`

**解决方案**:
```bash
# 确保 npm 已安装
npm --version

# 重新安装 Claude CLI
npm install -g @anthropic-ai/claude-code

# 检查 PATH 环境变量
echo $PATH
```

### 问题 4: Gemini API 调用失败

**症状**: `API key not valid` 错误

**解决方案**:
1. 检查 API Key 是否正确
2. 检查网络连接
3. 检查 Google Cloud 项目配额

---

## Docker 支持（可选）

如果使用 Docker，可以参考以下 Dockerfile：

```dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . /app
WORKDIR /app

# 默认命令
CMD ["python3", "main.py", "--help"]
```

---

## 最低配置运行

如果系统资源有限，可以：

1. **减少评论数量**: 使用 `--max-reviews` 参数
2. **使用 CLI 本地模式**: 避免额外的网络开销
3. **分批处理**: 将大文件分成小批次处理

示例：
```bash
python3 main.py "reviews.csv" --max-reviews 50 --mode 3
```

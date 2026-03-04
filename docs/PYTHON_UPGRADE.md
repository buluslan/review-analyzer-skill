# Python 环境升级指南

## 为什么要升级？

Python 3.9.6 已于 **2024年10月停止支持（EOL）**，这意味着：

- 不再接收安全更新和bug修复
- Google和其他第三方库可能停止支持
- 潜在的安全漏洞和兼容性问题
- 错过性能优化和新特性

## 推荐版本

| Python版本 | 状态 | 特点 |
|------------|------|------|
| **3.10.x** | 稳定版 | 成熟稳定，广泛兼容 |
| **3.11.x** | 性能增强版 | 比3.10快15-60%，推荐用于新项目 |
| **3.12.x** | 最新版 | 最新特性，但部分库可能尚未完全适配 |

**推荐选择**：Python 3.11.7 或更高版本

---

## macOS 升级步骤

### 方法1: 使用 Homebrew（推荐）

```bash
# 安装 Python 3.11
brew install python@3.11

# 创建软链接（可选）
ln -s -f /usr/local/opt/python@3.11/bin/python3.11 /usr/local/bin/python3

# 验证安装
python3.11 --version
```

### 方法2: 使用 pyenv（推荐用于多版本管理）

```bash
# 安装 pyenv（如果未安装）
brew install pyenv

# 配置 shell（根据您的 shell 选择）
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# 安装 Python 3.11.7
pyenv install 3.11.7

# 设置为全局默认版本
pyenv global 3.11.7

# 或仅对当前项目设置
cd /path/to/review-analyzer
pyenv local 3.11.7

# 验证版本
python --version
```

### 方法3: 官方安装包

1. 访问 [Python官网](https://www.python.org/downloads/macos/)
2. 下载 Python 3.11.x 安装包
3. 运行安装程序并按提示完成安装

---

## Linux 升级步骤

### Ubuntu/Debian

```bash
# 更新软件包列表
sudo apt update

# 安装必要依赖
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev wget

# 下载 Python 3.11.7
wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz

# 解压并编译
tar -xf Python-3.11.7.tgz
cd Python-3.11.7
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall

# 验证安装
python3.11 --version
```

### 使用 pyenv（推荐）

```bash
# 安装依赖
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev \
liblzma-dev python-openssl git

# 安装 pyenv
curl https://pyenv.run | bash

# 配置 shell
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# 安装 Python 3.11.7
pyenv install 3.11.7
pyenv global 3.11.7
```

### CentOS/RHEL

```bash
# 安装依赖
sudo yum groupinstall -y "Development Tools"
sudo yum install -y openssl-devel bzip2-devel libffi-devel zlib-devel wget

# 下载并编译 Python 3.11.7
wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz
tar -xf Python-3.11.7.tgz
cd Python-3.11.7
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall

# 验证安装
python3.11 --version
```

---

## Windows 升级步骤

### 方法1: 官方安装包（推荐）

1. 访问 [Python官网](https://www.python.org/downloads/windows/)
2. 下载 Python 3.11.x Windows installer（64-bit）
3. 运行安装程序，**务必勾选 "Add Python to PATH"**
4. 选择 "Install Now" 或 "Customize installation"

### 方法2: 使用 Windows Package Manager (winget)

```powershell
# 以管理员身份运行 PowerShell
winget install Python.Python.3.11

# 验证安装
python --version
```

### 方法3: 使用 Anaconda/Miniconda

```bash
# 创建新环境
conda create -n review-analyzer python=3.11

# 激活环境
conda activate review-analyzer

# 验证版本
python --version
```

---

## 升级后操作

### 1. 重新安装项目依赖

进入项目目录并重新安装所有依赖：

```bash
cd /path/to/review-analyzer

# 使用新版本 Python 安装依赖
pip3.11 install -r requirements.txt

# 或使用 python -m pip（推荐）
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. 验证依赖安装

```bash
# 检查已安装的包
python -m pip list

# 检查特定包版本
python -c "import google.generativeai; print(google.generativeai.__version__)"
python -c "import pandas; print(pandas.__version__)"
```

### 3. 运行环境检查脚本

```bash
python scripts/check_environment.py
```

### 4. 测试项目功能

```bash
# 运行主程序测试
python main.py examples/reviews_sample.csv --creator "Test"
```

---

## 常见问题和解决方案

### Q1: 升级后出现 "ModuleNotFoundError" 错误

**原因**: 新Python环境未安装项目依赖

**解决方案**:
```bash
python -m pip install -r requirements.txt
```

### Q2: pip 仍然指向旧版本

**原因**: 多个Python版本共存时，pip命令可能指向旧版本

**解决方案**:
```bash
# 使用 python -m pip 确保使用正确的版本
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 或创建 pip 别名
alias pip3.11='python3.11 -m pip'
```

### Q3: Virtualenv 仍然使用旧Python版本

**原因**: 虚拟环境绑定到创建时的Python版本

**解决方案**:
```bash
# 删除旧虚拟环境
rm -rf venv/

# 使用新Python版本创建新虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 重新安装依赖
pip install -r requirements.txt
```

### Q4: Google Generative AI 库版本不兼容

**原因**: 某些库版本可能需要更新

**解决方案**:
```bash
# 更新到最新兼容版本
python -m pip install --upgrade google-generativeai

# 或指定兼容版本
python -m pip install google-generativeai==0.8.4
```

### Q5: 权限错误（Linux/macOS）

**原因**: 系统Python目录需要管理员权限

**解决方案**:
```bash
# 使用用户目录安装（推荐）
python -m pip install --user -r requirements.txt

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Q6: macOS "zsh: bad CPU type in executable" 错误

**原因**: 架构不匹配（Intel vs Apple Silicon）

**解决方案**:
```bash
# 重新安装为正确架构
arch -x86_64 pyenv install 3.11.7  # Intel
arch -arm64 pyenv install 3.11.7    # Apple Silicon

# 或使用 Rosetta（Apple Silicon上运行Intel版本）
arch -x86_64 brew install python@3.11
```

---

## 版本兼容性说明

### Python 3.9 vs 3.10 vs 3.11 特性对比

| 特性 | Python 3.9 | Python 3.10 | Python 3.11 |
|------|-----------|-------------|-------------|
| 性能基准 | 100% | 110% | 150-160% |
| 异常链 | `raise ... from` | 增强 `*` 捕获 | 更好错误提示 |
| 类型提示 | `list[str]` | `X \| Y` 联合类型 | `Self` 类型 |
| 字典合并 | `x \| y` | 改进 | 更快实现 |

### 项目依赖兼容性

所有 `requirements.txt` 中的依赖均支持 Python 3.10+：

```
✅ google-generativeai  - 支持 3.8+
✅ pandas              - 支持 3.9+
✅ requests            - 支持 3.7+
✅ beautifulsoup4      - 支持 3.7+
✅ jinja2              - 支持 3.7+
✅ python-dotenv       - 支持 3.7+
✅ apify-client        - 支持 3.8+
✅ tqdm                - 支持 3.7+
```

---

## 推荐工具

### pyenv - Python版本管理器

**优势**:
- 轻松切换多个Python版本
- 为不同项目设置不同版本
- 避免系统Python冲突

**安装**:
```bash
# macOS
brew install pyenv

# Linux
curl https://pyenv.run | bash

# Windows (使用 pyenv-win)
pip install pyenv-win --target %USERPROFILE%\.pyenv
```

### virtualenv - 虚拟环境管理

**优势**:
- 项目隔离，避免依赖冲突
- 轻量级，快速创建

**使用**:
```bash
python -m venv venv
source venv/bin/activate  # 激活
deactivate                # 退出
```

---

## 升级检查清单

完成以下步骤确保升级成功：

- [ ] 安装 Python 3.11.x
- [ ] 验证 Python 版本 (`python --version`)
- [ ] 创建/更新虚拟环境
- [ ] 安装项目依赖 (`pip install -r requirements.txt`)
- [ ] 运行环境检查脚本 (`python scripts/check_environment.py`)
- [ ] 测试项目功能 (`python main.py examples/reviews_sample.csv`)
- [ ] 更新 IDE/编辑器配置（如果需要）
- [ ] 更新 CI/CD 配置（如果适用）

---

## 获取帮助

如果升级过程中遇到问题：

1. 运行环境检查脚本诊断问题
2. 查看 [故障排除文档](TROUBLESHOOTING.md)
3. 在 GitHub 提交 Issue

---

## 参考资料

- [Python官方下载页面](https://www.python.org/downloads/)
- [pyenv文档](https://github.com/pyenv/pyenv)
- [Python 3.11新特性](https://docs.python.org/3.11/whatsnew/3.11.html)
- [Google AI SDK文档](https://ai.google.dev/docs)

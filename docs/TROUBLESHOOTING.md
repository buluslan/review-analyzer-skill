# 故障排除指南

> **解决常见问题和错误**

本指南提供常见问题的解决方案和调试技巧。

---

## 目录

- [快速诊断](#快速诊断)
- [安装问题](#安装问题)
- [运行时问题](#运行时问题)
- [AI 分析问题](#ai-分析问题)
- [输出问题](#输出问题)
- [性能问题](#性能问题)
- [API 问题](#api-问题)
- [获取帮助](#获取帮助)

---

## 快速诊断

### 运行诊断脚本

```bash
python scripts/verify_installation.py
```

**诊断内容**:
- ✅ Python 版本
- ✅ 依赖包安装
- ✅ Claude Code CLI 状态
- ✅ Gemini API 配置
- ✅ 文件完整性

### 检查清单

在报告问题前，请确认：

- [ ] Python 版本 >= 3.9
- [ ] 已安装所有依赖包
- [ ] Claude Code CLI 已安装
- [ ] 输入文件格式正确
- [ ] 有足够的磁盘空间
- [ ] 网络连接正常（如使用 Gemini）

---

## 安装问题

### 问题 1：Python 版本过低

**错误信息**:
```
TypeError: 'type' object is not subscriptable
```

**原因**: Python 版本低于 3.9

**解决方案**:

```bash
# 检查 Python 版本
python --version

# 升级 Python
# macOS
brew install python@3.11

# Linux (Ubuntu)
sudo apt install python3.11

# Windows: 从 python.org 下载安装包
```

---

### 问题 2：pip 安装失败

**错误信息**:
```
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案**:

```bash
# 升级 pip
python -m pip install --upgrade pip

# 清除缓存
pip cache purge

# 使用国内镜像（中国用户）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 问题 3：依赖包冲突

**错误信息**:
```
ERROR: pip's dependency resolver does not currently take into account...
```

**解决方案**:

```bash
# 方案 1：使用虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 方案 2：强制重新安装
pip install --force-reinstall -r requirements.txt

# 方案 3：忽略依赖冲突（不推荐）
pip install --no-deps -r requirements.txt
```

---

### 问题 4：Claude CLI 找不到

**错误信息**:
```
❌ 找不到 Claude Code CLI！请确保已安装 Claude Code
```

**原因**:
- Claude CLI 未安装
- Claude CLI 未在 PATH 中

**解决方案**:

```bash
# 1. 重新安装 Claude CLI
npm install -g @anthropic-ai/claude-code

# 2. 检查安装位置
which claude  # macOS/Linux
where claude  # Windows

# 3. 手动添加到 PATH
# macOS/Linux: 添加到 ~/.bashrc 或 ~/.zshrc
export PATH="$PATH:$HOME/.npm-global/bin"

# Windows: 系统设置 → 环境变量 → Path
```

---

### 问题 5：虚拟环境激活失败

**Windows PowerShell 错误**:
```
无法加载文件 venv\Scripts\Activate.ps1，因为在此系统上禁止运行脚本
```

**解决方案**:

```powershell
# 临时允许脚本执行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 激活虚拟环境
venv\Scripts\Activate.ps1
```

**永久解决**:
```powershell
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 运行时问题

### 问题 1：找不到输入文件

**错误信息**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'data/reviews.csv'
```

**解决方案**:

```bash
# 1. 检查文件路径
ls -la data/reviews.csv  # macOS/Linux
dir data\reviews.csv     # Windows

# 2. 使用绝对路径
python main.py /full/path/to/data/reviews.csv

# 3. 使用相对路径
python main.py ../data/reviews.csv
```

---

### 问题 2：CSV 格式错误

**错误信息**:
```
pandas.errors.ParserError: Error tokenizing data...
```

**原因**: CSV 文件格式不正确

**解决方案**:

1. **检查 CSV 编码**:

```bash
# 检查文件编码
file -I reviews.csv  # macOS/Linux

# 转换为 UTF-8
iconv -f GBK -t UTF-8 input.csv > output.csv
```

2. **检查 CSV 格式**:

```csv
# 正确格式
内容,打分,时间
这个产品很好用！,5,2024-01-15
质量不错，物流快。,5,2024-01-14
```

3. **使用 Excel 另存为 CSV UTF-8**:
- 打开 Excel 文件
- 文件 → 另存为
- 格式选择 "CSV UTF-8 (逗号分隔)(*.csv)"

---

### 问题 3：缺少必需列

**错误信息**:
```
ValueError: CSV 文件缺少必需列: ['评论内容']
```

**解决方案**:

1. **检查列名**:

```bash
# 查看列名
python -c "import pandas as pd; df = pd.read_csv('data/reviews.csv'); print(df.columns)"
```

2. **重命名列**:

```python
import pandas as pd

# 读取 CSV
df = pd.read_csv('data/reviews.csv')

# 重命名列
df.rename(columns={
    'review': '内容',
    'rating': '打分',
    'date': '时间'
}, inplace=True)

# 保存
df.to_csv('data/reviews_fixed.csv', index=False)
```

3. **支持的列名**:

| 类型 | 支持的列名 |
|------|-----------|
| 评论内容 | 内容、评价、body、review |
| 评分 | 打分、rating、score、stars |
| 时间 | 时间、date、日期 |

---

### 问题 4：权限错误

**错误信息**:
```
PermissionError: [Errno 13] Permission denied: 'output/...'
```

**解决方案**:

```bash
# macOS/Linux
chmod +w output/
sudo chown -R $USER output/

# Windows: 以管理员身份运行
# 右键 → 以管理员身份运行
```

---

## AI 分析问题

### 问题 1：Claude CLI 调用失败

**错误信息**:
```
❌ Claude CLI 调用失败！请检查 Claude Code 是否正确安装
```

**原因**:
- Claude CLI 未安装
- Claude CLI 未登录
- 命令路径错误

**解决方案**:

```bash
# 1. 检查 Claude CLI
claude --version

# 2. 重新登录
claude auth login

# 3. 测试命令
claude "Hello, Claude!"

# 4. 检查配置
claude auth whoami
```

---

### 问题 2：AI 打标速度慢

**现象**: 打标阶段耗时过长

**优化方案**:

```bash
# 1. 减少处理数量
python main.py data/reviews.csv --max-reviews 100

# 2. 增大批次
python main.py data/reviews.csv --batch-size 50

# 3. 调整并发数（编辑 src/config.py）
MAX_CONCURRENT_WORKERS = 15
```

---

### 问题 3：AI 打标质量差

**现象**: 标签不准确或不完整

**解决方案**:

1. **检查提示词**: 查看 `src/prompts/templates.py`
2. **调整标签体系**: 编辑 `references/tag_system.yaml`
3. **增加样本量**: 使用更多评论数据
4. **清理数据**: 去除无效或重复评论

---

### 问题 4：洞察生成失败

**错误信息**:
```
❌ 洞察生成失败: ...
```

**解决方案**:

```bash
# 1. 检查 CSV 数据质量
# 确保有足够的打标数据

# 2. 使用 CLI 模式
python main.py data/reviews.csv --insights-mode 1

# 3. 检查内存
# 减少处理数量
python main.py data/reviews.csv --max-reviews 200
```

---

## 输出问题

### 问题 1：HTML 报告无法打开

**现象**: HTML 文件空白或无法显示

**原因**:
- 浏览器不兼容
- 文件路径错误
- 文件损坏

**解决方案**:

```bash
# 1. 使用现代浏览器
# Chrome, Firefox, Edge, Safari

# 2. 检查文件大小
ls -lh output/*/可视化洞察报告_*.html

# 3. 重新生成
python main.py data/reviews.csv --insights-mode 2
```

---

### 问题 2：CSV 文件乱码

**现象**: Excel 打开 CSV 显示乱码

**解决方案**:

1. **使用 UTF-8 编码打开**:
   - Excel → 数据 → 从文本/CSV 导入
   - 文件原始格式选择 "UTF-8"

2. **转换为 GBK**:

```python
import pandas as pd

# 读取 UTF-8
df = pd.read_csv('output.csv', encoding='utf-8')

# 保存为 GBK
df.to_csv('output_gbk.csv', encoding='gbk', index=False)
```

3. **直接用文本编辑器打开**:
   - VS Code
   - Sublime Text
   - Notepad++

---

### 问题 3：输出目录为空

**现象**: `output/` 目录没有生成文件

**解决方案**:

```bash
# 1. 检查日志输出
# 查看错误信息

# 2. 检查磁盘空间
df -h  # macOS/Linux

# 3. 手动指定输出目录（编辑 main.py）
# 或检查 src/config.py 中的输出配置

# 4. 重新运行
python main.py data/reviews.csv --verbose
```

---

## 性能问题

### 问题 1：内存不足

**错误信息**:
```
MemoryError: ...
```

**解决方案**:

```bash
# 1. 减少批次大小
python main.py data/reviews.csv --batch-size 20

# 2. 减少处理数量
python main.py data/reviews.csv --max-reviews 100

# 3. 减少并发数（编辑 src/config.py）
MAX_CONCURRENT_WORKERS = 5

# 4. 使用 64 位 Python
python --version
# 确保显示 64-bit
```

---

### 问题 2：处理速度慢

**现象**: 整体处理耗时过长

**优化方案**:

```bash
# 1. 使用 Gemini 快速模式
python main.py data/reviews.csv --insights-mode 2

# 2. 增大批次
python main.py data/reviews.csv --batch-size 50

# 3. 增加并发
# 编辑 src/config.py: MAX_CONCURRENT_WORKERS = 15

# 4. 减少数据量
python main.py data/reviews.csv --max-reviews 200

# 5. 使用 SSD
# 将项目和数据放在 SSD 上
```

---

### 问题 3：CPU 占用高

**现象**: CPU 占用率 100%

**原因**: AI 分析阶段使用多并发

**解决方案**:

```bash
# 1. 减少并发数（编辑 src/config.py）
MAX_CONCURRENT_WORKERS = 5

# 2. 降低批次大小
python main.py data/reviews.csv --batch-size 20

# 3. 关闭其他应用程序
# 释放 CPU 资源
```

---

## API 问题

### 问题 1：Gemini API Key 无效

**错误信息**:
```
❌ Gemini API Key 无效或未配置
```

**解决方案**:

```bash
# 1. 获取新的 API Key
# 访问: https://aistudio.google.com/app/apikey

# 2. 设置环境变量
export GEMINI_API_KEY="your-new-api-key"

# 3. 或运行时输入
python main.py data/reviews.csv --insights-mode 2
# 按提示输入新的 API Key
```

---

### 问题 2：Gemini API 调用失败

**错误信息**:
```
⚠️ Gemini API 调用失败，已回退到 CLI 模式
```

**原因**:
- 网络连接问题
- API 配额用尽
- API 服务异常

**解决方案**:

```bash
# 1. 检查网络连接
ping aistudio.google.com

# 2. 检查 API 配额
# 访问: https://aistudio.google.com/app/usage

# 3. 重试
python main.py data/reviews.csv --insights-mode 2

# 4. 使用 CLI 模式
python main.py data/reviews.csv --insights-mode 1
```

---

### 问题 3：API 请求超时

**错误信息**:
```
Timeout: Gemini API 请求超时
```

**解决方案**:

```bash
# 1. 检查网络速度
speedtest-cli

# 2. 使用 VPN（如果需要）
# 3. 重试请求
python main.py data/reviews.csv --insights-mode 2

# 4. 使用 CLI 模式
python main.py data/reviews.csv --insights-mode 1
```

---

## 调试技巧

### 启用详细日志

编辑 `src/config.py`:

```python
# 启用详细日志
VERBOSE = True
DEBUG = True
```

### 查看完整错误信息

```bash
# 使用 Python 详细模式
python -v main.py data/reviews.csv

# 查看堆栈跟踪
python -c "import traceback; ..."
```

### 测试单个模块

```bash
# 测试数据加载
python -c "from src.data_loader import load_data; print(load_data('data/reviews.csv'))"

# 测试 AI 分析
python -c "from src.review_analyzer import analyze_review; print(analyze_review('测试评论'))"
```

### 检查中间输出

```python
# 在 main.py 中添加调试代码
print(f"加载数据: {len(df)} 条")
print(f"打标完成: {len(tagged_df)} 条")
print(f"生成洞察: {len(insights)} 字符")
```

---

## 获取帮助

### 自助资源

1. **文档资源**:
   - [快速开始](QUICKSTART.md)
   - [安装指南](INSTALLATION.md)
   - [高级用法](ADVANCED_USAGE.md)
   - [架构说明](ARCHITECTURE.md)

2. **诊断工具**:
   ```bash
   python scripts/verify_installation.py
   ```

### 社区支持

1. **GitHub Issues**:
   - 搜索已有问题
   - 提交新的 Issue 到 [review-analyzer](https://github.com/buluslan/review-analyzer/issues)
   - 提供详细信息

2. **GitHub Discussions**:
   - 提问和讨论
   - 分享使用经验
   - 最佳实践

### 报告问题指南

提交 Issue 时，请包含：

1. **系统信息**:
   ```bash
   python --version
   pip list
   uname -a  # macOS/Linux
   systeminfo  # Windows
   ```

2. **错误信息**:
   - 完整的错误堆栈
   - 错误发生的步骤

3. **输入数据**:
   - 数据样本（脱敏）
   - CSV 文件格式

4. **配置信息**:
   - 使用的命令行参数
   - 配置文件内容

---

## 常见错误代码

| 错误代码 | 说明 | 解决方案 |
|---------|------|----------|
| `FileNotFoundError` | 文件不存在 | 检查文件路径 |
| `PermissionError` | 权限不足 | 检查文件权限 |
| `MemoryError` | 内存不足 | 减少数据量或批次 |
| `TimeoutError` | 请求超时 | 检查网络或重试 |
| `ValueError` | 值错误 | 检查输入数据格式 |
| `TypeError` | 类型错误 | 检查数据类型 |
| `ImportError` | 导入错误 | 安装缺失的依赖包 |
| `SyntaxError` | 语法错误 | 检查代码或配置文件 |

---

**遇到其他问题？**

1. 运行诊断脚本
2. 查看文档资源
3. 搜索 GitHub Issues
4. 提交新的 Issue

**我们在这里帮助您！** 🤝

# 高级用法

> **掌握高级功能和自定义配置**

本指南介绍工具的高级功能，包括双模洞察系统、批量处理、自定义配置等。

---

## 目录

- [双模洞察系统](#双模洞察系统)
- [批量处理](#批量处理)
- [自定义配置](#自定义配置)
- [高级命令行参数](#高级命令行参数)
- [自定义标签体系](#自定义标签体系)
- [自定义提示词](#自定义提示词)
- [数据导出与集成](#数据导出与集成)
- [性能优化](#性能优化)

---

## 双模洞察系统

### 模式对比

| 特性 | CLI 深度模式 | Gemini 深度模式 |
|------|-------------|-----------------|
| **AI 引擎** | Claude CLI | Gemini 3.1 Flash / Gemini 3.1 Pro |
| **成本** | 使用 Claude 配额 | 需要 Gemini API Key |
| **速度** | 中等（~2 分钟） | 快速（~30 秒） |
| **质量** | 高质量 | 极大增强的推理质量 |
| **网络要求** | ❌ 不需要 | ✅ 需要 |
| **HTML 看板** | ❌ 不支持 | ✅ 支持 |
| **适用场景** | 深度分析 | 高质量深度分析 |

### 模式 1：CLI 深度模式（默认）

**特点**:
- ✅ 使用您的 Claude CLI 配额
- ✅ 深度推理，高质量分析
- ✅ 不产生额外 API 费用
- ✅ 离线可用（部分功能）

**使用方式**:

```bash
# 方式 1：默认模式
python main.py data/reviews.csv

# 方式 2：显式指定
python main.py data/reviews.csv --insights-mode 1
```

**输出**:
- ✅ CSV 标签数据
- ✅ Markdown 洞察报告
- ❌ HTML 可视化看板

**适用场景**:
- 深度产品分析
- 成本敏感场景
- 网络不稳定环境

### 模式 2：Gemini 深度模式

**特点**:
- ⚡ 快速生成洞察（4 倍速度提升）
- 🧠 推理质量极大增强
- 🎨 生成黑金奢华 HTML 看板
- 🌐 需要网络连接

**使用方式**:

```bash
# 方式 1：命令行指定
python main.py data/reviews.csv --insights-mode 2

# 方式 2：环境变量
export GEMINI_API_KEY="your-api-key"
python main.py data/reviews.csv --insights-mode 2

# 方式 3：交互式输入
python main.py data/reviews.csv
# 按提示选择模式 2，输入 API Key
```

**输出**:
- ✅ CSV 标签数据
- ✅ Markdown 洞察报告
- ✅ HTML 可视化看板（黑金奢华）

**适用场景**:
- 快速生成报告
- 需要可视化看板
- 批量处理多个产品

### 交互式模式选择

如果不指定 `--insights-mode`，程序会提示选择：

```
🤖 请选择 AI 引擎组合：
   [1] Claude CLI 模式
   [2] CLI+Gemini混动
   [3] Gemini增强模式 (推荐)
   输入编号 [默认 1]:
```

### API Key 管理

#### 临时输入

```bash
python main.py data/reviews.csv --insights-mode 2
# 程序会提示: 请输入 Gemini API Key:
```

#### 环境变量（推荐）

```bash
# macOS/Linux
export GEMINI_API_KEY="your-api-key"

# Windows (CMD)
set GEMINI_API_KEY=your-api-key

# Windows (PowerShell)
$env:GEMINI_API_KEY="your-api-key"
```

#### .env 文件

创建 `.env` 文件：

```bash
GEMINI_API_KEY=your-api-key-here
```

**安全提示**:
- ✅ 将 `.env` 添加到 `.gitignore`
- ❌ 不要将 `.env` 提交到版本控制
- ❌ 不要在公开代码中暴露 API Key

---

## 批量处理

### 处理单个文件

```bash
# 基本用法
python main.py data/reviews.csv

# 指定产品信息
python main.py data/reviews.csv --asin B08N5KWB9C --product-name "无线耳机"
```

### 处理多个产品

#### 方法 1：Shell 脚本（macOS/Linux）

创建 `batch_analyze.sh`:

```bash
#!/bin/bash

# 产品列表
ASINS=("B08N5KWB9C" "B0F9PP38BX" "B0DXK3B6B7")

# 循环处理
for asin in "${ASINS[@]}"; do
    echo "正在处理: $asin"
    python main.py "data/${asin}.csv" --asin "$asin" --insights-mode 2
    echo "完成: $asin"
done

echo "全部完成！"
```

运行：

```bash
chmod +x batch_analyze.sh
./batch_analyze.sh
```

#### 方法 2：批处理文件（Windows）

创建 `batch_analyze.bat`:

```batch
@echo off
setlocal

:: 产品列表
set ASINS=B08N5KWB9C B0F9PP38BX B0DXK3B6B7

:: 循环处理
for %%A in (%ASINS%) do (
    echo 正在处理: %%A
    python main.py "data\%%A.csv" --asin %%A --insights-mode 2
    echo 完成: %%A
)

echo 全部完成！
endlocal
```

运行：

```cmd
batch_analyze.bat
```

#### 方法 3：Python 脚本（跨平台）

创建 `batch_analyze.py`:

```python
#!/usr/bin/env python3
import subprocess
import sys

# 产品列表
products = [
    {"asin": "B08N5KWB9C", "file": "data/B08N5KWB9C.csv"},
    {"asin": "B0F9PP38BX", "file": "data/B0F9PP38BX.csv"},
    {"asin": "B0DXK3B6B7", "file": "data/B0DXK3B6B7.csv"},
]

# 循环处理
for product in products:
    print(f"\n正在处理: {product['asin']}")
    cmd = [
        sys.executable,
        "main.py",
        product["file"],
        "--asin", product["asin"],
        "--insights-mode", "2"
    ]
    subprocess.run(cmd)
    print(f"完成: {product['asin']}")

print("\n全部完成！")
```

运行：

```bash
python batch_analyze.py
```

### 性能优化建议

#### 批量大小调整

```bash
# 默认批次大小: 30 条评论
python main.py data/reviews.csv --batch-size 30

# 增大批次（提高速度，但增加内存占用）
python main.py data/reviews.csv --batch-size 50

# 减小批次（降低内存占用）
python main.py data/reviews.csv --batch-size 20
```

#### 并发控制

```bash
# 默认并发数: 10
# 在 src/config.py 中修改 MAX_CONCURRENT_WORKERS

# 调整并发数（根据系统性能）
# MAX_CONCURRENT_WORKERS = 15  # 增加并发
```

#### 限制处理数量

```bash
# 只处理前 100 条评论
python main.py data/reviews.csv --max-reviews 100

# 处理所有评论（默认最多 500 条）
python main.py data/reviews.csv --max-reviews 500
```

---

## 自定义配置

### 配置文件位置

主要配置文件：`src/config.py`

### 修改配置参数

```python
# ==================== 数据处理配置 ====================
# 最大处理评论数
MAX_REVIEWS: int = 500

# 批次大小
BATCH_SIZE: int = 30

# 最大并发工作数
MAX_CONCURRENT_WORKERS: int = 10

# ==================== 洞察报告生成配置 ====================
# 洞察生成模式: cli / gemini
INSIGHTS_PROVIDER: str = "cli"

# Gemini 模型配置
GEMINI_MODEL: str = "gemini-3.1-flash"  # 或 gemini-3.1-pro
GEMINI_TEMPERATURE: float = 0.7
GEMINI_MAX_TOKENS: int = 8192

# ==================== Claude CLI 配置 ====================
# Claude CLI 命令
CLAUADE_CLI_CMD: str = "claude"
```

### 环境变量配置

支持的环境变量：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `GEMINI_API_KEY` | Gemini API 密钥 | 空 |
| `MAX_REVIEWS` | 最大处理评论数 | 500 |
| `BATCH_SIZE` | 批次大小 | 30 |
| `INSIGHTS_PROVIDER` | 洞察模式 | cli |

使用示例：

```bash
export GEMINI_API_KEY="your-key"
export MAX_REVIEWS=200
export BATCH_SIZE=50
python main.py data/reviews.csv
```

---

## 高级命令行参数

### 完整参数列表

```bash
python main.py --help
```

### 常用参数组合

#### 场景 1：快速分析

```bash
# 小样本快速分析
python main.py data/reviews.csv --max-reviews 50 --insights-mode 2
```

#### 场景 2：深度分析

```bash
# 大样本深度分析
python main.py data/reviews.csv --max-reviews 500 --batch-size 20
```

#### 场景 3：指定创作者

```bash
# 在报告中显示创作者署名
python main.py data/reviews.csv --creator "Your Name" --insights-mode 2
```

#### 场景 4：自定义输出

```bash
# 指定 ASIN 和产品名称
python main.py data/reviews.csv \
    --asin B08N5KWB9C \
    --product-name "无线蓝牙耳机" \
    --creator "Your Name"
```

---

## 自定义标签体系

### 标签体系文件

标签定义位于：`references/tag_system.yaml`

### 标签维度说明

当前支持 22 个维度，分为 8 大类：

```yaml
# 人群维度 (4)
人群维度:
  - 性别
  - 年龄段
  - 职业
  - 购买角色

# 场景维度 (1)
场景维度:
  - 使用场景

# 功能维度 (2)
功能维度:
  - 满意度
  - 具体功能

# 质量维度 (3)
质量维度:
  - 材质
  - 做工
  - 耐用性

# 服务维度 (5)
服务维度:
  - 发货速度
  - 包装质量
  - 客服响应
  - 退换货
  - 保修

# 体验维度 (4)
体验维度:
  - 舒适度
  - 易用性
  - 外观设计
  - 价格感知

# 市场维度 (2)
市场维度:
  - 竞品对比
  - 复购意愿

# 情感维度 (1)
情感维度:
  - 总体评价
```

### 修改标签体系

1. 编辑 `references/tag_system.yaml`

2. 添加或修改标签：

```yaml
人群维度:
  - 性别
  - 年龄段
  - 职业
  - 购买角色
  - 地区  # 新增标签

# 新增维度
消费习惯:
  - 价格敏感度
  - 品牌忠诚度
```

3. 重新运行分析

**注意**: 修改标签体系后，需要确保 AI 提示词也相应更新。

---

## 自定义提示词

### 提示词模板位置

- **打标提示词**: `src/prompts/templates.py`
- **洞察提示词**: `src/prompts/templates.py`
- **参考文档**: `references/PROMPT_TEMPLATES_V1.md`

### 修改打标提示词

编辑 `src/prompts/templates.py` 中的 `get_tagging_prompt_txt` 函数。

### 修改洞察提示词

编辑 `src/prompts/templates.py` 中的 `get_insights_prompt_txt` 函数。

### 提示词最佳实践

1. **明确目标**: 清晰说明分析目标
2. **结构化输出**: 定义明确的输出格式
3. **示例引导**: 提供少量示例
4. **约束条件**: 明确约束和限制

---

## 数据导出与集成

### CSV 数据导出

生成的 CSV 文件可以直接在 Excel 中打开：

```bash
# macOS
open output/*/评论采集及打标数据_*.csv

# Windows
start output\*\评论采集及打标数据_*.csv
```

### 数据二次分析

使用 Python 进行二次分析：

```python
import pandas as pd

# 读取生成的 CSV
df = pd.read_csv('output/B08N5KWB9C-评论分析项目-2026-03-02/评论采集及打标数据_B08N5KWB9C.csv')

# 统计分析
print(df['总体评价'].value_counts())
print(df['年龄段'].value_counts())

# 导出统计结果
df['总体评价'].value_counts().to_csv('stats.csv')
```

### 与 BI 工具集成

支持的 BI 工具：
- ✅ Microsoft Excel
- ✅ Google Sheets
- ✅ Tableau
- ✅ Power BI
- ✅ Google Data Studio

### API 集成示例

将分析结果集成到现有系统：

```python
import requests
import json

# 读取分析结果
with open('output/*/分析洞察报告_*.md', 'r') as f:
    insights = f.read()

# 发送到 API
response = requests.post(
    'https://your-api.com/insights',
    json={'asin': 'B08N5KWB9C', 'insights': insights}
)
```

---

## 性能优化

### 打标阶段优化

#### 调整批次大小

```bash
# 增大批次（提高速度）
python main.py data/reviews.csv --batch-size 50

# 减小批次（降低内存）
python main.py data/reviews.csv --batch-size 20
```

#### 调整并发数

编辑 `src/config.py`:

```python
# 增加并发（需要更多内存）
MAX_CONCURRENT_WORKERS = 15

# 减少并发（节省内存）
MAX_CONCURRENT_WORKERS = 5
```

### 洞察生成优化

#### 使用 Gemini 深度模式

```bash
# 速度提升 4 倍，推理质量极大增强
python main.py data/reviews.csv --insights-mode 2
```

#### 限制输入数据

```bash
# 只分析前 100 条评论
python main.py data/reviews.csv --max-reviews 100
```

### 系统资源优化

#### 内存优化

- 使用 64 位 Python
- 增加系统虚拟内存
- 关闭其他应用程序

#### CPU 优化

- 使用多核 CPU
- 增加并发工作数
- 使用 SSD 存储

---

## 高级工作流

### 工作流 1：竞品对比分析

```bash
# 分析竞品 A
python main.py data/competitor_a.csv --asin B0AAAAAAA --creator "分析师A"

# 分析竞品 B
python main.py data/competitor_b.csv --asin B0BBBBBBB --creator "分析师A"

# 对比分析报告
# 使用 Excel 或 BI 工具对比两个 CSV 文件
```

### 工作流 2：定期监控

创建定时任务（crontab）：

```bash
# 每周一早上 9 点运行
0 9 * * 1 /path/to/project/batch_analyze.sh
```

### 工作流 3：客户反馈循环

```bash
# 1. 导出客户评论
# 从客服系统导出 CSV

# 2. 运行分析
python main.py feedback.csv --asin CUSTOM --creator "客服团队"

# 3. 生成报告
# 分享给产品和研发团队
```

---

## 故障排除

### 常见问题

详见 [故障排除指南](TROUBLESHOOTING.md)

### 获取帮助

- 📖 查看 [故障排除指南](TROUBLESHOOTING.md)
- 🐛 提交 [GitHub Issue](https://github.com/buluslan/ecommerce-review-analyzer/issues)
- 💬 参与 [GitHub Discussions](https://github.com/buluslan/ecommerce-review-analyzer/discussions)

---

## 下一步

- 📖 阅读 [架构说明](ARCHITECTURE.md) 了解系统设计
- 🔧 查看 [故障排除](TROUBLESHOOTING.md) 解决问题
- 📝 查看 [更新日志](CHANGELOG.md) 了解新功能

---

**高级用法难度**: ⭐⭐⭐☆☆（中高级）

**建议**: 熟悉基本用法后再尝试高级功能

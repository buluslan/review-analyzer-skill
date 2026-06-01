---
name: review-analyzer-skill
version: 2.0.0
author: Buluu@新西楼
description: |
  Agent 原生的电商评论深度分析工具 V2.0。
  支持22维度智能标签、14章深度洞察报告、6套主题可视化看板（共享基座+玻璃拟态）、Sorftime平台数据对接、飞书文档同步。

  当用户需要以下功能时触发：
  - 分析电商产品评论（Amazon等平台）
  - 从评论中提取用户画像、痛点和VOC（客户之声）
  - 生成产品洞察报告和机会点分析
  - 创建专业的可视化分析看板（6套主题可选）
  - 通过Sorftime获取产品评论数据
  - 将分析结果同步到飞书文档

  触发关键词：电商评论分析、评论分析、竞品分析、用户洞察、VOC分析、产品优化、市场调研、评论数据挖掘、Sorftime
license: MIT
allowed-tools:
  - bash
---

# Review Analyzer Skill V2.0 — Agent 原生版

AI驱动的电商评论深度分析工具，Agent原生设计，任何主流AI Coding Agent均可运行。

## 核心特性

- **22维度智能标签系统**: 人群/场景/功能/质量/服务/体验/市场/情感
- **14章深度洞察报告**: 洞察总览→用户画像→卖点痛点→改进建议→行动仪表盘→数据附录
- **6套主题可视化看板**: 共享基座架构，玻璃拟态质感（Premium Gold / Dark Tech / Linear Minimal / PostHog Analytics / Stripe Executive / Warm Editorial）
- **Sorftime数据对接**: 通过MCP/API/CLI获取亚马逊产品评论数据
- **飞书完整同步**: 文档 + 画板图表一键同步到飞书

## 快速开始

### 环境准备

```bash
pip install pandas jinja2 requests python-dotenv tqdm
```

### 数据输入方式

```bash
# 方式1: 本地CSV文件（原有方式）
python3 main.py "reviews.csv" --max-reviews 100 --creator "AI Assistant"

# 方式2: 从Sorftime获取数据
python3 main.py --source sorftime --asin B001OAXE0S --site US --max-reviews 100 --creator "AI Assistant"
```

## 工作流程

### 第一步：收集参数

❗ **必须使用 AskUserQuestion 工具依次收集**，严禁跳过或猜测用户意图。

**Q1: 数据来源**（必须）
- "本地CSV文件（上传文件路径）"
- "Sorftime平台获取（需要API Key，输入ASIN即可）"

**Q1.5: Sorftime字段选择**（仅当选择Sorftime时）
展示可用字段清单，必选字段已锁定（标题、正文、星级），推荐字段可勾选。

**Q2: 分析数量**（必须）
- "100条 (推荐) - 平衡速度与质量"
- "300条 - 更全面分析"
- "全部 - 分析所有评论"

**Q3: 飞书同步**（必须）
- "仅生成本地文件"
- "同步到飞书文档（需要lark-cli已安装且已认证）"

**Q4: 可视化模板**（可选）
- "否 — 不需要生成可视化HTML" — 跳过HTML看板生成
- "使用默认模板 (premium-gold)" — 直接使用默认模板
- "我想选择模板" — 展示以下6种可用模板：

| 模板 | 风格 | 适用场景 |
|------|------|---------|
| premium-gold | 金色奢华风 | 品牌展示、高管汇报 |
| posthog-analytics | 暖色分析风 | 数据分析、团队内部分享 |
| stripe-executive | 翡翠企业风 | 金融企业、投资决策 |
| linear-minimal | 极简蓝白风 | 产品评审、简洁汇报 |
| dark-tech | 暗色科技风 | 技术评审、数据密集场景 |
| warm-editorial | 暖纸编辑风 | 阅读分享、团队协作文档 |

**Q5: 报告署名**（⚠️ 仅当 Q4 选择了模板（非"否"）时才触发此问题）
- "默认：AI Assistant"
- "我想自定义署名"

### 第二步：执行分析

```bash
# 本地CSV模式（最小参数）
python3 main.py "<CSV文件路径>" \
  --max-reviews <数量> \
  --feishu-sync <true|false>

# 本地CSV模式（完整参数，含自定义模板和署名）
python3 main.py "<CSV文件路径>" \
  --max-reviews <数量> \
  --template <模板名> \
  --creator "<署名>" \
  --feishu-sync <true|false>

# Sorftime模式
python3 main.py \
  --source sorftime \
  --asin <ASIN> \
  --site US \
  --max-reviews <数量> \
  --feishu-sync <true|false>
```

### 第三步：展示结果

| 输出文件 | 内容 |
|---------|------|
| `评论采集及打标数据_{ASIN}.csv` | 22维度标签数据 |
| `分析洞察报告_{ASIN}.md` | 13章深度洞察报告 |
| `可视化洞察报告_{ASIN}.html` | 可视化看板（可选，用户选择模板时生成） |
| 飞书文档（可选） | 完整报告 + 画板图表 |

## 参考资料

- CSV格式要求: [references/csv_format.md](references/csv_format.md)
- 22维度标签: [references/tag_system.md](references/tag_system.md)
- 故障排除: [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)

## 作者

**Buluu@新西楼**
- GitHub: [@buluslan](https://github.com/buluslan)
- 主项目: [review-analyzer](https://github.com/buluslan/review-analyzer)

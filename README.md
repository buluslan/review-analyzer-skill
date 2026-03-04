<div align="center">

# Review Analyzer Skill
## 电商评论深度分析工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-1.0.0-black.svg)](https://github.com/buluslan/review-analyzer-skill)

**双模洞察系统 | 22维度智能标签 | 黑金奢华可视化看板**

Created By Buluu@新西楼

</div>

---

## 项目简介

Review Analyzer Skill 是一款AI驱动的电商评论深度分析工具，通过**双模洞察系统**为您提供灵活的分析选择：

- **CLI深度模式**：通过subprocess调用Claude CLI，使用您的Claude配额进行深度推理
- **Gemini快速模式**：使用Gemini API进行快速洞察生成（需要API Key，产生费用）

工具提供22维度智能标签、**黑金奢华可视化看板**、四位一体VOC系统（6套3D头像），是产品优化、竞品分析、市场调研的强大助手。

---

## 核心特性

### 🚀 双模洞察系统

| 模式 | AI引擎 | 成本说明 | 适用场景 |
|------|--------|----------|----------|
| **CLI深度模式** | Claude CLI | 使用您的Claude配额，不产生额外API费用 | 深度推理、高质量洞察 |
| **Gemini快速模式** | Gemini API | 需要API Key，约$0.001/产品 | 快速生成、批量分析 |

### 📊 22维度智能标签

全面覆盖评论信息的8大维度：

```
人群维度 (4): 性别、年龄段、职业、购买角色
场景维度 (1): 使用场景
功能维度 (2): 满意度、具体功能
质量维度 (3): 材质、做工、耐用性
服务维度 (5): 发货速度、包装质量、客服响应、退换货、保修
体验维度 (4): 舒适度、易用性、外观设计、价格感知
市场维度 (2): 竞品对比、复购意愿
情感维度 (1): 总体评价
```

### 🎨 黑金奢华可视化看板

**董事会高管汇报级别**的HTML报告：

- 鎏金黑金配色方案，专业大气
- 6个交互式Chart.js图表
- 动态数据可视化展示
- 鎏金渐变发光创作者署名
- 响应式设计，支持移动端查看

### 👥 四位一体VOC系统

立体化用户画像，增强社交质感：

- **6套3D头像**：商务/休闲/技术/儿童/银发族等
- **用户画像**：多维度用户特征分析
- **需求分析**：挖掘用户痛点和期望
- **原声呈现**：真实评论引用，增强说服力

### 📦 三位一体输出

| 输出文件 | 格式 | 内容说明 |
|---------|------|----------|
| `评论采集及打标数据_{ASIN}.csv` | CSV | 原始评论 + 22维度标签数据 |
| `分析洞察报告_{ASIN}.md` | Markdown | 深度洞察分析与建议 |
| `可视化洞察报告_{ASIN}.html` | HTML | 黑金奢华可视化看板 |

---

## 系统要求

| 要求 | 详情 |
|------|------|
| **操作系统** | macOS / Linux / Windows |
| **Python** | **3.10 或更高版本**（推荐 3.11.x） |
| **Claude CLI** | Claude Code CLI（CLI深度模式必需） |
| **Gemini API** | Gemini API Key（Gemini快速模式可选） |
| **内存** | 建议 4GB+ |
| **磁盘空间** | 建议 500MB+ |

> **提示**: Python 3.9.6 已停止支持，建议升级到 Python 3.11 或更高版本。运行 `python scripts/check_environment.py` 检查您的环境。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/buluslan/review-analyzer-skill.git
cd review-analyzer-skill
```

### 2. 环境检查（推荐）

```bash
# 检查Python版本和依赖
python scripts/check_environment.py
```

如果检查失败，请查看 [Python升级指南](docs/PYTHON_UPGRADE.md)

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装Claude CLI（CLI深度模式必需）

```bash
npm install -g @anthropic-ai/claude-code
```

### 5. 配置环境变量（可选）

如需使用Gemini快速模式：

```bash
cp .env.example .env
# 编辑.env文件，添加您的GEMINI_API_KEY
```

### 6. 运行分析

```bash
# CLI深度模式（使用Claude CLI，消耗Claude配额）
python main.py your_reviews.csv

# Gemini快速模式（需要GEMINI_API_KEY，产生API费用）
python main.py your_reviews.csv --insights-mode 2

# 指定创作者署名
python main.py your_reviews.csv --creator "Your Name"

# 自定义产品标题
python main.py your_reviews.csv --product-title "Amazing Product"
```

---

## CSV文件格式要求

工具支持自动模糊匹配列名，CSV文件需包含：

| 必需列 | 可选列名（模糊匹配） |
|--------|---------------------|
| 评论内容 | 内容/评价/body/review/text/comment |
| 评分 | 打分/rating/score/star |
| 时间（可选） | 时间/date/日期/time |

**示例**：详见 `examples/reviews_sample.csv`

---

## 输出示例

运行完成后，将在 `output/` 目录生成三种报告：

### 1. CSV标签数据
```csv
评论内容,评分,性别,年龄段,职业,购买角色,使用场景,满意度...
"The quality is amazing",5,女性,25-34岁,白领,自用,家用办公,高...
```

### 2. Markdown洞察报告
```markdown
# 产品分析洞察报告

## 核心发现
- 用户满意度：92%
- 主要优势：材质优良、设计美观
- 改进建议：优化包装、增强耐用性
...
```

### 3. HTML可视化看板
- 黑金奢华配色
- 交互式图表
- 动态数据展示
- 创作者署名（鎏金发光效果）

---

## 使用场景

### 场景1：产品优化
分析自己产品的评论，发现用户痛点，优化产品功能和设计。

### 场景2：竞品分析
分析竞品评论，了解竞争对手的优势和劣势，寻找差异化机会。

### 场景3：市场调研
批量分析多个产品的评论，了解市场需求、用户偏好和行业趋势。

### 场景4：用户洞察
深度了解目标用户群体，构建精准用户画像，优化营销策略。

---

## 项目结构

```
review-analyzer-skill/
├── src/                          # 核心源代码
│   ├── config.py                 # 配置管理
│   ├── data_loader.py            # 数据加载与预处理
│   ├── review_analyzer.py        # AI分析引擎
│   ├── user_persona_analyzer.py  # 用户画像分析
│   ├── insights_generator.py     # 洞察生成器
│   ├── report_generator.py       # 报告生成器
│   └── prompts/                  # 提示词模板
│       └── templates.py
├── assets/                       # 静态资源
│   ├── report.html               # HTML报告模板
│   └── avatars/                  # 6套3D头像
├── references/                   # 参考文档
│   ├── tag_system.yaml          # 22维度标签定义
│   └── architecture.md          # 系统架构说明
├── docs/                        # 用户文档
│   ├── QUICKSTART.md            # 快速开始
│   ├── PYTHON_UPGRADE.md        # Python升级指南
│   └── CHANGELOG.md             # 更新日志
├── examples/                    # 示例数据
│   ├── reviews_sample.csv       # 示例CSV
│   └── output_sample/           # 示例输出
├── main.py                      # 主入口
├── requirements.txt             # Python依赖
├── .env.example                 # 环境变量模板
├── LICENSE                      # MIT许可证
└── README.md                    # 项目说明
```

---

## 常见问题

<details>
<summary><b>Q1: CLI模式和Gemini模式有什么区别？</b></summary>

**A**: **CLI深度模式**通过subprocess调用您的Claude CLI，使用您的Claude配额进行深度推理，不产生额外API费用。**Gemini快速模式**使用Gemini API快速生成洞察，需要API Key，会产生API费用（约$0.001/产品）。

**选择建议**：
- 需要深度洞察、已订阅Claude → 使用CLI深度模式
- 需要快速分析、愿意支付小额API费用 → 使用Gemini快速模式
</details>

<details>
<summary><b>Q2: 为什么需要Claude CLI？</b></summary>

**A**: CLI深度模式需要Claude CLI进行AI推理。这是使用您的Claude配额进行深度分析的前提条件。

**安装方法**：
```bash
npm install -g @anthropic-ai/claude-code
```
</details>

<details>
<summary><b>Q3: 如何获取Gemini API Key？</b></summary>

**A**: 访问 [Google AI Studio](https://aistudio.google.com/app/apikey) 创建API Key。Gemini模式是可选的，不使用也不影响核心功能。

**费用说明**：约$0.001/产品，具体以Google官方定价为准。
</details>

<details>
<summary><b>Q4: CSV文件格式有什么要求？</b></summary>

**A**: CSV文件需要包含以下列（支持模糊匹配）：
- **评论内容**：内容/评价/body/review
- **评分**：打分/rating/score
- **时间**：时间/date/日期（可选）

详见 `examples/reviews_sample.csv`
</details>

<details>
<summary><b>Q5: 如何升级Python版本？</b></summary>

**A**: Python 3.9.6 已停止支持，建议升级到 Python 3.11 或更高版本。

**检查环境**：
```bash
python scripts/check_environment.py
```

**升级指南**：详见 [Python升级指南](docs/PYTHON_UPGRADE.md)

**快速升级**：
```bash
# macOS (使用 Homebrew)
brew install python@3.11

# 或使用 pyenv (推荐)
pyenv install 3.11.7
pyenv global 3.11.7
```
</details>

<details>
<summary><b>Q6: 支持哪些电商平台？</b></summary>

**A**: 理论上支持所有提供评论导出的电商平台：
- Amazon（推荐）
- eBay
- AliExpress
- Shopee
- 淘宝/天猫
- 其他CSV格式评论数据
</details>

---

## 与其他工具对比

| 特性 | Review Analyzer Skill | 其他工具 |
|------|----------------------|---------|
| **洞察模式** | CLI深度 + Gemini快速双模 | 通常单一模式 |
| **数据源** | 本地CSV，隐私安全 | 多为在线服务 |
| **输出** | CSV+HTML+MD三位一体 | 格式单一 |
| **视觉风格** | 黑金奢华看板 | 传统报表 |
| **VOC系统** | 四位一体+6套3D头像 | 基础画像 |
| **CLI模式成本** | 使用Claude配额 | 多不支持 |
| **Gemini模式成本** | API付费（约$0.001/产品） | API付费 |
| **离线使用** | CLI模式支持 | 通常不支持 |

---

## 路线图

- [x] **v1.0.0** - 首个正式发布
  - 双模洞察系统（CLI + Gemini）
  - 22维度智能标签
  - 黑金奢华可视化看板
  - 四位一体VOC系统
- [ ] **v1.1.0** - 多平台增强
  - eBay/AliExpress专用适配器
  - 更多平台预设模板
- [ ] **v1.2.0** - 云端部署版本
  - Docker容器化
  - 一键部署脚本
- [ ] **v2.0.0** - API服务模式
  - RESTful API接口
  - Web Dashboard

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 致谢

- 感谢 Anthropic 提供 Claude AI
- 感谢 Google 提供 Gemini API
- 灵感源自开源社区的智慧贡献

---

## 技术支持

- **Issues**: [GitHub Issues](https://github.com/buluslan/review-analyzer-skill/issues)
- **文档**: [完整文档](docs/)
- **示例**: [示例输出](examples/output_sample/)

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐️**

Made with ❤️ by Buluu@新西楼

[⬆ 返回顶部](#review-analyzer-skill)

</div>

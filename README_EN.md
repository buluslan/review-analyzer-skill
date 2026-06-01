# 评论深度分析Skill

<div align="center">

# Review Analyzer Skill

**An AI-powered deep analysis tool for multi-scenario review content**

**For the latest AI industry trends, AI + e-commerce/advertising practices, and thoughts on human-AI collaboration, follow the WeChat Official Account: 【新西楼】**
![qrcode_for_gh_e3b954bd3859_258](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-black.svg)](https://github.com/buluslan/review-analyzer-skill)
[![English](https://img.shields.io/badge/lang-English-blue.svg)](README_EN.md)
[![中文](https://img.shields.io/badge/lang-中文-red.svg)](README.md)

**14-Chapter Deep Insight Report | 6 Themed Visualization Dashboards | Feishu Document Sync | Agent-Native Architecture**

**Created By Buluu@新西楼**

</div>

---

## Project Overview

Review Analyzer Skill is an **Agent-native** deep review analysis tool for multi-scenario content, compatible with mainstream AI Coding Agents such as Claude Code and OpenCode. It supports local CSV data import and [Sorftime](https://www.sorftime.com/) platform integration, and runs with zero API keys.

### V2.0 Core Upgrades

| Feature | V1.0 | V2.0 |
|---------|------|------|
| Analysis Engine | Gemini API + CLI dual mode | **CLI single mode** (zero API Key) |
| Data Source | Local CSV | **Local CSV + Sorftime platform** |
| Insight Report | 7-chapter basic analysis | **14-chapter deep insight** (with action decision dashboard) |
| Visualization Dashboard | 1 black-gold template | **6 themed templates** (Glassmorphism + Chart.js theming) |
| Feishu Integration | None | **Full sync** (documents + whiteboard + mermaid diagrams) |
| Architecture | Python scripts | **Agent-native Skill** (SKILL.md instruction-driven) |
| Tagging Concurrency | 2 | **4** (50% faster) |

### Workflow

```
Data Input: Local CSV or Sorftime platform
     ↓
Phase 1: AI Deep Tagging (concurrency 4, 22-dimension tags)
Phase 2: User Persona identification (3-4 personas, 3 positive + 3 negative Golden Samples)
Phase 3: Insight Report generation (14-chapter structured report)
Phase 4: Unified output (MD + HTML Dashboard + Feishu sync)
```

> 📄 **[View the full Insight Report example online (Feishu document)](https://my.feishu.cn/docx/GMv7dBzlXo5wblxVaWGclEernib)** — includes 14 complete chapters + Feishu whiteboard mermaid diagrams

---

## Core Features

### 📊 22-Dimension Smart Tags

Comprehensive coverage across 8 major dimensions of review information:

```
Demographic (4): Gender, Age Group, Occupation, Purchase Role
Scenario (1): Usage Scenario
Functional (2): Satisfaction, Specific Features
Quality (3): Material, Craftsmanship, Durability
Service (5): Shipping Speed, Packaging Quality, Customer Service Response, Returns & Exchanges, Warranty
Experience (4): Comfort, Ease of Use, Exterior Design, Price Perception
Market (2): Competitive Comparison, Repurchase Intent
Sentiment (1): Overall Evaluation
```

### 🎨 6 Themed Visualization Dashboards

HTML reports **ready for work presentations**, with a Shared Base architecture ensuring unified content structure:

| Theme | Style | Best For |
|-------|-------|----------|
| premium-gold | Black & Gold Luxury + Playfair Display | Executive presentations, brand showcases |
| dark-tech | Cyberpunk + Cyan + Frosted Glass | Technical teams, data-driven |
| linear-minimal | Minimalist White & Blue + Clear Glass | Product reviews, clean presentations |
| posthog-analytics | Warm White & Orange + Warm Glass | Data analysis, operational reviews |
| stripe-executive | Emerald Green + Emerald Glass | Finance & enterprise, investment decisions |
| warm-editorial | Paper & Copper + Paper Glass | Brand reports, editorial style |

Each dashboard includes: 11 sections, interactive Chart.js charts (themed color palettes), responsive design, and Glassmorphism card effects.

### 📋 14-Chapter Deep Insight Report

1. Insight Overview (core findings + strategic direction + market positioning)
2. Core User Personas (multi-dimensional profiles + core needs + verbatim quotes)
3. Key Selling Points & Value Validation (data-backed + user quotes)
4. Major Pain Points & Negative Attribution (severity + cascade effects + action recommendations)
5. Improvement Suggestions & Priorities (P0/P1/P2 + expected benefits)
6. Potential Opportunities & Differentiation (data + suggestions)
7. Typical User Deep Analysis
8-12. In-depth content chapters
13. Action Decision Dashboard
14. Data Appendix

### 📦 Multi-format Output + Feishu Sync

| Output | Format | Description |
|--------|--------|-------------|
| Tagging Data | CSV | Raw reviews + 22-dimension tags |
| Insight Report | Markdown | 14-chapter deep analysis |
| Visualization Dashboard | HTML | 6 themes available, Glassmorphism |
| Feishu Document | — | Auto-sync report + mermaid whiteboard |

---

## System Requirements

| Requirement | Details |
|-------------|---------|
| **Operating System** | macOS / Linux / Windows |
| **Python** | **3.10 or higher** (3.11.x recommended) |
| **Agent CLI** | Any AI Coding Agent such as Claude Code CLI or OpenCode CLI |
| **Memory** | 4GB+ recommended |
| **Feishu Sync (optional)** | Requires [lark-cli](https://github.com/germalli/lark-cli) installed and authenticated |

> **Feishu Sync Note**: To sync analysis results to Feishu documents, install `lark-cli` in advance (`npm install -g lark-cli`) and complete `lark-cli login` authentication. If not installed, the tool will automatically skip the Feishu sync step without affecting other features.

---

## Quick Start

### Option 1: Install via skills.sh ecosystem (recommended)

```bash
npx skills add buluslan/review-analyzer-skill
```

After installation, invoke directly with natural language in Claude Code:

```bash
# Example 1: Analyze a specific file
Please analyze the reviews for this product: reviews.csv

# Example 2: Describe your need
Help me do a deep analysis of competitor reviews
```

### Option 2: Manually clone the repository

```bash
git clone https://github.com/buluslan/review-analyzer-skill.git
cd review-analyzer-skill
pip install -r requirements.txt
```

### Run Parameters

```bash
# === Data Input Methods ===

# Method 1: Local CSV file
python3 main.py your_reviews.csv --max-reviews 200

# Method 2: Sorftime platform data (requires SORFTIME_API_KEY configuration)
python3 main.py --source sorftime --asin B09XYZ123 --site US --max-reviews 200

# === Full Parameters ===
python3 main.py your_reviews.csv \
  --asin B09XYZ123 \
  --template premium-gold \
  --feishu-sync auto \
  --concurrent 4 \
  --creator "Your Name"

# === Visualization Template (choose from 6, or "none" to skip) ===
--template premium-gold|dark-tech|linear-minimal|posthog-analytics|stripe-executive|warm-editorial|none

# === Feishu Sync (requires lark-cli installed and authenticated) ===
--feishu-sync auto|manual|skip

# === Quick Replay (skip tagging, run Phase 2-5 from a pre-tagged CSV) ===
python3 replay_phase2to5.py output/B09XYZ123-评论分析项目-6.1/评论采集及打标数据_B09XYZ123.csv
```

---

## CSV File Format Requirements

The tool supports automatic fuzzy matching of column names. CSV files should contain:

| Required Column | Accepted Column Names (fuzzy match) |
|-----------------|--------------------------------------|
| Review Content | 内容/评价/body/review/text/comment |
| Rating | 打分/rating/score/star |
| Date (optional) | 时间/date/日期/time |

**Example**: See `examples/reviews_sample.csv` for details.

---

## Output Examples

After the run completes, the following files will be generated in the `output/` directory:

### 1. CSV Tagging Data
```csv
Review Content,Rating,Gender,Age Group,Occupation,Purchase Role,Usage Scenario,Satisfaction...
"The quality is amazing",5,Female,25-34,Office Worker,Personal Use,Home Office,High...
```

### 2. Markdown Insight Report
```markdown
# Product Analysis Insight Report

## Core Findings
- User Satisfaction: 92%
- Key Strengths: Premium materials, beautiful design
- Improvement Suggestions: Optimize packaging, enhance durability
...
```

### 3. HTML Visualization Dashboard
- Black & gold luxury color scheme
- Interactive charts
- Dynamic data display
- Creator signature (gilded glow effect)

---

## Use Cases

### Case 1: Product Optimization
Analyze your own product reviews to discover user pain points and optimize product features and design.

### Case 2: Competitive Analysis
Analyze competitor reviews to understand their strengths and weaknesses, and identify differentiation opportunities.

### Case 3: Market Research
Batch-analyze reviews across multiple products to understand market demand, user preferences, and industry trends.

### Case 4: User Insights
Deeply understand your target user groups, build precise User Personas, and optimize marketing strategies.

---

## Project Structure

```
review-analyzer-skill/
├── main.py                      # V2.0 main entry (4-Phase workflow)
├── SKILL.md                     # Agent instruction file (Claude Code Skill)
├── replay_phase2to5.py          # Quick replay script (skip tagging)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── src/
│   ├── config.py                # CLI single mode configuration
│   ├── template_engine.py       # Unified template engine (Jinja2 SSR + Shared Base)
│   ├── chart_engine.py          # Chart.js chart configuration generation
│   ├── insights_generator.py    # 14-chapter Insight Report generation (CLI subprocess)
│   ├── output_manager.py        # Output management (MD + HTML + Feishu sync)
│   ├── feishu_sync.py           # Feishu document + whiteboard sync
│   ├── report_generator.py      # Report generation (compatibility layer)
│   ├── data_fetchers/           # Data access layer (Sorftime + CSV)
│   ├── prompts/                 # 14-chapter Prompt system
│   └── templates/               # Visualization Dashboard templates
│       ├── base/                # Shared Base
│       │   ├── dashboard_base.html   # Base HTML (Jinja2)
│       │   └── dashboard_base.css    # Base layout CSS
│       ├── premium-gold/        # Black-gold theme
│       ├── dark-tech/           # Cyberpunk theme
│       ├── linear-minimal/      # Minimalist blue-white theme
│       ├── posthog-analytics/   # Warm orange analytics theme
│       ├── stripe-executive/    # Emerald enterprise theme
│       └── warm-editorial/      # Newspaper editorial theme
├── assets/                      # Static resources (3D avatars)
├── examples/                    # Sample data + output examples
├── tools/                       # Utility scripts
├── references/                  # Reference documentation
└── docs/                        # User documentation
```

---

## FAQ

<details>
<summary><b>Q1: What are the differences between V2.0 and V1.0?</b></summary>

**A**: V2.0 is a comprehensive upgrade:
- **Zero API Key**: Removed Gemini dependency, unified to CLI single mode
- **14-chapter report**: Expanded from 7 chapters to 14 chapters of deep insight
- **6 themed dashboards**: Expanded from 1 to 6 (with Glassmorphism effects)
- **Feishu sync**: Auto-sync documents + mermaid whiteboards
- **Shared Base architecture**: Fix bugs in one place; adding a new theme requires only one CSS file
</details>

<details>
<summary><b>Q2: Do I need any API Key?</b></summary>

**A**: V2.0 **requires no API Key whatsoever**. It uses the built-in models of Claude Code / OpenCode throughout, consuming your Claude quota.
</details>

<details>
<summary><b>Q3: What are the CSV file format requirements?</b></summary>

**A**: The CSV file needs to contain the following columns (fuzzy matching supported):
- **Review Content**: 内容/评价/body/review
- **Rating**: 打分/rating/score
- **Date** (optional): 时间/date/日期

See `examples/reviews_sample.csv` for details.
</details>

<details>
<summary><b>Q4: How do I choose a visualization template?</b></summary>

**A**: The 6 templates correspond to different scenarios:
- **premium-gold**: Executive presentations, brand showcases (default)
- **dark-tech**: Technical teams, data analysis
- **linear-minimal**: Product reviews, clean presentations
- **posthog-analytics**: Operational reviews, growth analysis
- **stripe-executive**: Finance & enterprise, investment decisions
- **warm-editorial**: Brand reports, magazine style

Use `--template none` to skip dashboard generation.
</details>

<details>
<summary><b>Q5: Which e-commerce platforms are supported?</b></summary>

**A**: In theory, all e-commerce platforms that provide review exports are supported: Amazon, eBay, AliExpress, Shopee, Taobao/Tmall, and any other CSV-format review data.
</details>

---

## Comparison with Other Tools

| Feature | Review Analyzer Skill V2.0 | Other Tools |
|---------|---------------------------|-------------|
| **Architecture** | Agent-native Skill | Typically standalone scripts |
| **API Key** | Zero (pure CLI) | Most require API keys |
| **Insight Report** | 14-chapter deep analysis | Basic statistics |
| **Visualization** | 6 themes + Glassmorphism | Single template or none |
| **Feishu Integration** | Document + whiteboard auto-sync | Mostly unsupported |
| **Data Privacy** | Local processing, no third-party uploads | Mostly online services |
| **Template Extension** | New theme = 1 CSS file | Requires full rewrite |

---

## Roadmap

- [x] **v1.0.0** - First official release (22-dimension tags + dual mode + HTML dashboard)
- [x] **v2.0.0** - Agent-native version (14-chapter report + 6 themes + Feishu sync + Shared Base architecture)
- [ ] **v2.1.0** - Web enhancements (frontend template selector + screenshot export)
- [ ] **v3.0.0** - Multi-platform analysis (batch ASIN + competitive comparison reports)

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

- Thanks to Anthropic for providing Claude AI
- Thanks to Google for providing Gemini API
- Inspired by the wisdom and contributions of the open-source community

### Contributors

Thanks to the following community contributors for their contributions to this project:

| Contributor | Contribution |
|-------------|-------------|
| [@zeropool](https://github.com/zeropool) | OpenCode CLI engine support, URL remote input, avatar asset compression ([PR#1](https://github.com/buluslan/review-analyzer-skill/pull/1)) |

> Community contributors submit PRs, and the maintenance team conducts code reviews. To ensure code quality and stability, some PRs may be merged as improved versions rather than direct merges of the original submissions.

---

## Technical Support

- **Issues**: [GitHub Issues](https://github.com/buluslan/review-analyzer-skill/issues)
- **Contact the Builder (please note 【github】)**:
<img width="717" height="714" alt="wechat_2025-10-17_173400_583" src="https://github.com/user-attachments/assets/7c406098-dcd9-4684-84bd-f0ed4213e95f" />

---

<div align="center">

**If this project helps you, please give it a ⭐️**

Made with ❤️ by Buluu@新西楼

**Built for cross-border e-commerce professionals ❤️**

[⬆ Back to Top](#review-analyzer-skill)

</div>

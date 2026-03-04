# E-commerce Review Deep Analysis Skill

<div align="center">

# Review Analyzer Skill

**An AI-Powered Multi-Scenario Review Content Deep Analysis Tool**

For the latest AI industry insights, AI+ecommerce/advertising practices, and reflections on human-AI collaboration, follow our WeChat Official Account: 【新西楼】

![qrcode_for_gh_e3b954bd3859_258](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-1.0.0-black.svg)](https://github.com/buluslan/review-analyzer-skill)
[![English](https://img.shields.io/badge/lang-English-blue.svg)](README_EN.md)
[![中文](https://img.shields.io/badge/lang-中文-red.svg)](README.md)

**22-Dimension Smart Tags | Deep Insight Reports | Dynamic Visual Dashboards**

**Created By Buluu@新西楼**

</div>

---

## Project Introduction

Review Analyzer Skill is an AI-driven multi-scenario review content deep analysis tool, providing flexible analysis mode options:

- **Claude CLI Local Mode**: Use your built-in model in Claude Code for tagging, reasoning, report and dashboard generation.
- **Gemini Enhanced Mode (Recommended)**: Call Gemini API, use [Gemini 3.1 flash] to generate insight reports, use [Gemini 3.1 pro] to generate visualization dashboards (requires API Key, incurs fees)
- **Claude CLI + Gemini Hybrid Mode**: Text reports use Claude Code built-in model, visualization dashboards use [Gemini 3.1 pro] (requires API Key, incurs fees)

To improve token usage efficiency, the default for tag mining is to use your built-in model in Claude Code.

This tool comes with 8 dimensions and 22 general-purpose tags, rigorous insight analysis report templates, and high-quality visualization dashboards, making it a powerful assistant for product optimization, competitive analysis, and market research.

---

## Core Features

### 📊 22-Dimension Smart Tags

Comprehensive coverage of 8 major dimensions of review information:

```
Demographics (4): Gender, Age Group, Occupation, Purchase Role
Usage Scenario (1): Usage Scenario
Functionality (2): Satisfaction Level, Specific Features
Quality (3): Material, Workmanship, Durability
Service (5): Shipping Speed, Packaging Quality, Customer Service, Returns/Exchanges, Warranty
Experience (4): Comfort, Ease of Use, Appearance Design, Price Perception
Market (2): Competitive Comparison, Repurchase Intent
Sentiment (1): Overall Rating
```

### 🎨 Premium Black-Gold Dashboard

HTML reports **ready for work presentations**:

- Luxurious black-gold color scheme, professional and elegant
- 6 interactive Chart.js charts
- Dynamic data visualization
- Gradient glowing creator signature
- Responsive design, mobile-friendly viewing

### 👥 4-in-1 VOC System

Multi-dimensional user profiling with enhanced social appeal:

- **6 Sets of 3D Avatars**: Business/Casual/Tech/Kids/Seniors/etc.
- **User Profiles**: Multi-dimensional user characteristic analysis
- **Needs Analysis**: Dig deep into user pain points and expectations
- **Voice of Customer**: Authentic review quotes to enhance persuasion

### 📦 Three-in-One Output

| Output File | Format | Content Description |
|-------------|--------|---------------------|
| `评论采集及打标数据_{ASIN}.csv` | CSV | Raw reviews + 22-dimension tag data |
| `分析洞察报告_{ASIN}.md` | Markdown | Deep insight analysis and recommendations |
| `可视化洞察报告_{ASIN}.html` | HTML | Premium visualization dashboard |

---

## System Requirements

| Requirement | Details |
|-------------|---------|
| **Operating System** | macOS / Linux / Windows |
| **Python** | **3.10 or higher** (3.11.x recommended) |
| **Claude CLI** | Claude Code CLI (Required for CLI Local Mode) |
| **Gemini API** | Gemini API Key (Optional for Gemini Enhanced Mode) |
| **Memory** | 4GB+ recommended |
| **Disk Space** | 500MB+ recommended |

> **Note**: Python 3.9.6 is no longer supported. Upgrade to Python 3.11 or higher is recommended. Run `python scripts/check_environment.py` to check your environment.

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/buluslan/review-analyzer-skill.git
cd review-analyzer-skill
```

### 2. Environment Check (Recommended)

```bash
# Check Python version and dependencies
python scripts/check_environment.py
```

If check fails, see [Python Upgrade Guide](docs/PYTHON_UPGRADE.md)

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Claude CLI (Required for CLI Mode)

```bash
npm install -g @anthropic-ai/claude-code
```

### 5. Configure Environment Variables (Optional)

For Gemini Enhanced Mode:

```bash
cp .env.example .env
# Edit .env file, add your GEMINI_API_KEY
```

### 6. Run Analysis

```bash
# CLI Local Mode (Uses Claude CLI, consumes Claude quota)
python main.py your_reviews.csv

# Gemini Enhanced Mode (Requires GEMINI_API_KEY, incurs API fees)
python main.py your_reviews.csv --insights-mode 2

# Specify creator signature
python main.py your_reviews.csv --creator "Your Name"

# Custom product title
python main.py your_reviews.csv --product-title "Amazing Product"
```

---

## CSV File Format Requirements

The tool supports automatic fuzzy column matching. CSV files need to include:

| Required Columns | Optional Column Names (Fuzzy Match) |
|------------------|-------------------------------------|
| Review Content | 内容/评价/body/review/text/comment |
| Rating | 打分/rating/score/star |
| Time (Optional) | 时间/date/日期/time |

**Example**: See `examples/reviews_sample.csv`

---

## Output Examples

After completion, three types of reports will be generated in the `output/` directory, with custom folder support:

### 1. CSV Tag Data
```csv
Review Content,Rating,Gender,Age Group,Occupation,Purchase Role,Usage Scenario,Satisfaction...
"The quality is amazing",5,Female,25-34,White Collar,Personal Use,Home Office,High...
```

### 2. Markdown Insight Report
```markdown
# Product Analysis Insight Report

## Key Findings
- User Satisfaction: 92%
- Main Advantages: Excellent material, beautiful design
- Improvement Suggestions: Optimize packaging, enhance durability
...
```

### 3. HTML Visualization Dashboard
- Black-gold luxurious color scheme
- Interactive charts
- Dynamic data display
- Creator signature (gradient glowing effect)

---

## Use Cases

### Scenario 1: Product Optimization
Analyze your own product reviews to discover user pain points and optimize product features and design.

### Scenario 2: Competitive Analysis
Analyze competitor reviews to understand their strengths and weaknesses, finding differentiation opportunities.

### Scenario 3: Market Research
Batch analyze multiple product reviews to understand market demands, user preferences, and industry trends.

### Scenario 4: User Insights
Deeply understand target user groups, build accurate user profiles, and optimize marketing strategies.

---

## Project Structure

```
review-analyzer-skill/
├── src/                          # Core source code
│   ├── config.py                 # Configuration management
│   ├── data_loader.py            # Data loading and preprocessing
│   ├── review_analyzer.py        # AI analysis engine
│   ├── user_persona_analyzer.py  # User profile analysis
│   ├── insights_generator.py     # Insight generator
│   ├── report_generator.py       # Report generator
│   └── prompts/                  # Prompt templates
│       └── templates.py
├── assets/                       # Static resources
│   ├── report.html               # HTML report template
│   └── avatars/                  # 6 sets of 3D avatars
├── references/                   # Reference documents
│   ├── tag_system.yaml          # 22-dimension tag definitions
│   └── architecture.md          # System architecture documentation
├── docs/                        # User documentation
│   ├── QUICKSTART.md            # Quick start guide
│   ├── PYTHON_UPGRADE.md        # Python upgrade guide
│   └── CHANGELOG.md             # Change log
├── examples/                    # Example data
│   ├── reviews_sample.csv       # Sample CSV
│   └── output_sample/           # Sample output
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── LICENSE                      # MIT License
└── README.md                    # Project documentation
```

---

## FAQ

<details>
<summary><b>Q1: What's the difference between CLI Mode and Gemini Mode?</b></summary>

**A**: **CLI Local Mode** uses your Claude Code to complete the full tagging-report-dashboard process without additional API fees. **Gemini Enhanced Mode** uses Gemini API to generate insight reports and dashboards, requiring an API Key and incurring API fees.

**Selection Advice**:
- Need quick insights → Use Claude Code CLI mode, all processes use built-in models
- Need deep analysis, willing to pay small API fees → Use Gemini Enhanced Mode, calls Gemini for report generation and visualization dashboards
</details>

<details>
<summary><b>Q2: Why do I need Claude CLI?</b></summary>

**A**: CLI Local Mode requires Claude CLI for AI reasoning. This is a prerequisite for using your Claude quota for deep analysis.

**Installation Method**:
```bash
npm install -g @anthropic-ai/claude-code
```
</details>

<details>
<summary><b>Q3: How to get Gemini API Key?</b></summary>

**A**: Visit [Google AI Studio](https://aistudio.google.com/app/apikey) to create an API Key. Gemini mode is optional; not using it doesn't affect core functionality.

**Cost Note**: Specific pricing is subject to Google's official pricing.
</details>

<details>
<summary><b>Q4: What are the CSV file format requirements?</b></summary>

**A**: CSV files need to include the following columns (supports fuzzy matching):
- **Review Content**: 内容/评价/body/review
- **Rating**: 打分/rating/score
- **Time**: 时间/date/日期 (optional)

See `examples/reviews_sample.csv` for details
</details>

<details>
<summary><b>Q5: How to upgrade Python version?</b></summary>

**A**: Python 3.9.6 is no longer supported. Upgrade to Python 3.11 or higher is recommended.

**Check Environment**:
```bash
python scripts/check_environment.py
```

**Upgrade Guide**: See [Python Upgrade Guide](docs/PYTHON_UPGRADE.md)

**Quick Upgrade**:
```bash
# macOS (using Homebrew)
brew install python@3.11

# Or use pyenv (recommended)
pyenv install 3.11.7
pyenv global 3.11.7
```
</details>

<details>
<summary><b>Q6: Which e-commerce platforms are supported?</b></summary>

**A**: Theoretically supports all e-commerce platforms that provide review export:
- Amazon (recommended)
- eBay
- AliExpress
- Shopee
- Taobao/Tmall
- Other CSV format review data
</details>

---

## Comparison with Other Tools

| Feature | Review Analyzer Skill | Other Tools |
|---------|----------------------|-------------|
| **Insight Modes** | Dual-Mode: CLI Local + Gemini Enhanced | Usually single mode |
| **Data Source** | Local CSV, privacy secure | Mostly online services |
| **Output** | Three-in-One: CSV+HTML+MD | Single format |
| **Visual Style** | Premium black-gold dashboard | Traditional reports |
| **VOC System** | 4-in-1 + 6 sets of 3D avatars | Basic profiles |
| **CLI Mode Cost** | Uses Claude quota | Mostly unsupported |
| **Gemini Mode Cost** | API paid | API paid |

---

## Roadmap

- [x] **v1.0.0** - First official release
  - Dual-Mode Insight System (CLI + Gemini)
  - 22-Dimension Smart Tags
  - Premium Black-Gold Visualization Dashboard
  - 4-in-1 VOC System
- [ ] **v1.1.0** - Multi-platform enhancement
  - eBay/AliExpress dedicated adapters
  - More platform preset templates
- [ ] **v1.2.0** - Cloud deployment version
  - Docker containerization
  - One-click deployment scripts
- [ ] **v2.0.0** - API service mode
  - RESTful API interface
  - Web Dashboard

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

- Thanks to Anthropic for providing Claude AI
- Thanks to Google for providing Gemini API
- Inspired by the wisdom contributions of the open source community

---

## Technical Support

- **Issues**: [GitHub Issues](https://github.com/buluslan/review-analyzer-skill/issues)
- **Contact Builder, please mention 【github】**:
<img width="717" height="714" alt="wechat_2025-10-17_173400_583" src="https://github.com/user-attachments/assets/7c406098-dcd9-4684-84bd-f0ed4213e95f" />

---

<div align="center">

**If this project helps you, please give a ⭐️**

Made with ❤️ by Buluu@新西楼

**Built for cross-border e-commerce practitioners ❤️**

[⬆ Back to Top](#review-analyzer-skill)

</div>

# 快速开始指南

> **5 分钟上手 E-commerce Review Analyzer**

本指南将帮助您在最短的时间内运行工具并生成第一份分析报告。

---

## 前置条件检查

在开始之前，请确保您的系统满足以下要求：

### 1. Python 版本

```bash
python --version
# 或
python3 --version
```

**要求**: Python 3.9 或更高版本

### 2. Claude Code CLI

```bash
claude --version
```

**要求**: 已安装 Claude Code CLI

**如果未安装**:
```bash
npm install -g @anthropic-ai/claude-code
```

---

## 第一步：获取项目

### 方式 1：直接下载

1. 访问 [GitHub 仓库](https://github.com/buluslan/ecommerce-review-analyzer)
2. 点击 "Code" → "Download ZIP"
3. 解压到本地目录

### 方式 2：Git 克隆（推荐）

```bash
git clone https://github.com/buluslan/ecommerce-review-analyzer.git
cd ecommerce-review-analyzer
```

---

## 第二步：安装依赖

```bash
pip install -r requirements.txt
```

**依赖说明**:
- `pandas`: 数据处理
- `jinja2`: HTML 报告生成
- `python-dotenv`: 环境变量管理
- `google-generativeai`: Gemini API（可选）

---

## 第三步：准备数据

### 使用示例数据（最快）

项目包含示例数据，可直接使用：

```bash
python main.py examples/reviews_sample.csv
```

### 使用自己的数据

1. 准备 CSV 文件，包含以下列（系统自动模糊匹配）：
   - **评论内容**: 内容/评价/body/review
   - **评分**: 打分/rating/score
   - **时间**: 时间/date/日期（可选）

2. 最简单的 CSV 格式：

```csv
内容,打分
这个产品很好用！质量不错，物流也快。,5
一般般吧，包装有点破损。,3
用了两天就坏了，太差了。,1
```

---

## 第四步：运行分析

### 基础用法（CLI 深度模式）

```bash
python main.py your_reviews.csv
```

**特点**:
- ✅ 使用您的 Claude CLI 配额
- ✅ 深度推理，高质量分析
- ✅ 不产生额外 API 费用

### 指定产品信息

```bash
# 指定 ASIN
python main.py your_reviews.csv --asin B08N5KWB9C

# 指定产品名称
python main.py your_reviews.csv --product-name "无线蓝牙耳机"
```

### 使用 Gemini 深度模式（可选）

```bash
python main.py your_reviews.csv --insights-mode 2
```

**特点**:
- ⚡ 快速生成洞察
- 🧠 推理质量极大增强
- 🎨 生成黑金奢华 HTML 看板

**获取 Gemini API Key**:
1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建新的 API Key
3. 运行时按提示输入

---

## 第五步：查看输出

### 输出位置

分析完成后，输出文件位于：

```
output/{ASIN}-评论分析项目-{日期}/
├── 评论采集及打标数据_{ASIN}.csv
├── 分析洞察报告_{ASIN}.md
└── 可视化洞察报告_{ASIN}.html
```

### 输出文件说明

#### 1. CSV 数据文件

**文件名**: `评论采集及打标数据_{ASIN}.csv`

**内容**: 原始评论 + 22 维度智能标签

**标签维度**:
- 人群维度(4): 性别、年龄段、职业、购买角色
- 场景维度(1): 使用场景
- 功能维度(2): 满意度、具体功能
- 质量维度(3): 材质、做工、耐用性
- 服务维度(5): 发货、包装、客服、退换货、保修
- 体验维度(4): 舒适度、易用性、外观、价格
- 市场维度(2): 竞品对比、复购意愿
- 情感维度(1): 总体评价

**用途**:
- 导入 Excel 进行二次分析
- 数据透视表统计
- 用户行为研究

#### 2. Markdown 洞察报告

**文件名**: `分析洞察报告_{ASIN}.md`

**内容**:
- 🎯 核心用户画像（4 位一体 VOC 系统）
- 💡 产品优势与不足
- 🔥 高频关键词云
- 📊 改进建议

**用途**:
- 产品优化参考
- 营销策略制定
- 竞品分析报告

#### 3. HTML 可视化看板

**文件名**: `可视化洞察报告_{ASIN}.html`

**内容**:
- 🎨 黑金奢华高管汇报级设计
- 📊 6 个交互式 Chart.js 图表
- 👥 6 套 3D 用户头像
- ✨ 鎏金渐变发光创作者署名

**用途**:
- 向领导/客户演示
- 生成专业报告
- 社交媒体分享

**打开方式**: 直接用浏览器打开 HTML 文件

---

## 完整示例

### 从零到报告

```bash
# 1. 进入项目目录
cd ecommerce-review-analyzer

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行示例数据
python main.py examples/reviews_sample.csv

# 4. 等待分析完成（约 3-5 分钟）

# 5. 查看输出
open output/B08N5KWB9C-评论分析项目-2026-03-02/可视化洞察报告_B08N5KWB9C.html
```

---

## 常用命令速查

```bash
# 基础分析（CLI 模式）
python main.py data/reviews.csv

# 指定 ASIN 和创作者
python main.py data/reviews.csv --asin B08N5KWB9C --creator "Your Name"

# 限制处理评论数
python main.py data/reviews.csv --max-reviews 100

# Gemini 深度模式
python main.py data/reviews.csv --insights-mode 2

# 查看帮助
python main.py --help
```

---

## 下一步

- 📖 阅读 [安装指南](INSTALLATION.md) 了解详细配置
- 🚀 查看 [高级用法](ADVANCED_USAGE.md) 掌握批量处理
- 🔧 阅读 [架构说明](ARCHITECTURE.md) 了解系统设计
- 💡 遇到问题？查看 [故障排除](TROUBLESHOOTING.md)

---

## 获取帮助

### 文档资源

- **GitHub Issues**: [提交问题](https://github.com/buluslan/ecommerce-review-analyzer/issues)
- **讨论区**: [GitHub Discussions](https://github.com/buluslan/ecommerce-review-analyzer/discussions)

### 快速诊断

如果遇到问题，运行诊断脚本：

```bash
python scripts/verify_installation.py
```

---

**预计时间**: 5 分钟

**难度**: ⭐☆☆☆☆（非常简单）

**准备好了吗？开始您的第一次分析！** 🚀

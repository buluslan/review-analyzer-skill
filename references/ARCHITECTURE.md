# 系统架构说明

> **深入了解系统设计和技术实现**

本文档详细说明 E-commerce Review Analyzer 的系统架构、模块设计和数据流程。

---

## 目录

- [概述](#概述)
- [系统架构](#系统架构)
- [目录结构](#目录结构)
- [核心模块](#核心模块)
- [数据流程](#数据流程)
- [AI 引擎](#ai-引擎)
- [标签体系](#标签体系)
- [报告生成](#报告生成)
- [技术栈](#技术栈)
- [扩展指南](#扩展指南)

---

## 概述

### 设计理念

E-commerce Review Analyzer 采用模块化设计，遵循以下原则：

1. **分离关注点**: 每个模块负责单一功能
2. **可扩展性**: 易于添加新功能和集成
3. **可维护性**: 代码清晰，文档完善
4. **性能优化**: 支持并发处理和批量操作

### 核心特性

- 🎯 **三模 AI 引擎**: CLI全程模式 + 混动模式 + Gemini增强模式
- 🏷 **22 维度智能标签**: 全方位评论分析
- 👥 **四位一体 VOC 系统**: 立体化用户画像
- 🎨 **黑金奢华看板**: 高管汇报级可视化
- 📊 **数据闭环机制**: 结构化输出

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  CLI 命令 │  │ 批处理脚本 │  │ API 集成 │  │  Skill  │    │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘    │
└────────┼────────────┼────────────┼────────────┼────────────┘
         │            │            │            │
         └────────────┴────────────┴────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                         主控制层                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │              main.py (主入口)                     │       │
│  │  - 参数解析                                        │       │
│  │  - 流程编排                                        │       │
│  │  - 模式选择                                        │       │
│  └───────────────────┬──────────────────────────────┘       │
└──────────────────────┼──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                         业务逻辑层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 数据加载模块   │  │ AI 分析模块   │  │ 报告生成模块  │      │
│  │ data_loader  │  │ review_...   │  │ report_...   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 用户画像模块   │  │ 洞察生成模块   │  │ 配置管理模块  │      │
│  │ user_persona │  │ insights_... │  │   config     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                         AI 引擎层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  CLI 模式     │  │  混动模式     │  │ Gemini 模式   │      │
│  │  Claude CLI  │  │ CLI+Gemini   │  │ Gemini API   │      │
│  │  (全程本地)   │  │ (混动)       │  │ (全程API)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                         数据存储层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  CSV 文件  │  │ HTML 报告  │  │ Markdown  │  │ 配置文件  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构

### 完整目录树

```
ecommerce-review-analyzer/
├── main.py                           # 主入口（CLI 命令行）
│
├── src/                              # 源代码目录
│   ├── __init__.py
│   ├── config.py                     # 全局配置管理
│   ├── data_loader.py                # 数据加载器
│   ├── review_analyzer.py            # AI 评论分析引擎
│   ├── user_persona_analyzer.py      # 用户画像分析器
│   ├── insights_generator.py         # 洞察报告生成器
│   ├── report_generator.py           # 可视化报告生成器
│   └── prompts/                      # 提示词模块
│       ├── __init__.py
│       └── templates.py              # AI 提示词模板
│
├── assets/                           # 静态资源目录
│   ├── report.html                   # HTML 报告模板
│   └── avatars/                      # 3D 头像库（6 套）
│       ├── business/                 # 商务风格头像
│       ├── casual/                   # 休闲风格头像
│       ├── tech/                     # 技术风格头像
│       ├── child/                    # 儿童风格头像
│       ├── senior/                   # 银发族风格头像
│       └── luxury/                   # 奢华风格头像
│
├── references/                       # 参考配置目录
│   ├── tag_system.yaml               # 22 维度标签体系
│   ├── PROMPT_TEMPLATES_V1.md        # 提示词参考文档
│   ├── user_personas.md              # VOC 系统说明
│   └── architecture.md               # 架构参考文档
│
├── docs/                             # 用户文档目录
│   ├── QUICKSTART.md                 # 快速开始指南
│   ├── INSTALLATION.md               # 安装指南
│   ├── ADVANCED_USAGE.md             # 高级用法
│   ├── TROUBLESHOOTING.md            # 故障排除
│   ├── ARCHITECTURE.md               # 架构说明（本文件）
│   └── CHANGELOG.md                  # 更新日志
│
├── examples/                         # 示例数据目录
│   ├── reviews_sample.csv            # 示例评论数据
│   └── output_sample/                # 示例输出
│       ├── 评论采集及打标数据_*.csv
│       ├── 分析洞察报告_*.md
│       └── 可视化洞察报告_*.html
│
├── scripts/                          # 辅助脚本目录
│   ├── verify_installation.py        # 安装验证脚本
│   ├── batch_analyze.py              # 批量处理脚本
│   └── install.sh                    # 安装脚本（可选）
│
├── output/                           # 输出目录（运行时生成）
│   └── {ASIN}-评论分析项目-{日期}/
│       ├── 评论采集及打标数据_{ASIN}.csv
│       ├── 分析洞察报告_{ASIN}.md
│       └── 可视化洞察报告_{ASIN}.html
│
├── requirements.txt                  # Python 依赖列表
├── .env.example                      # 环境变量模板
├── .gitignore                        # Git 忽略配置
├── LICENSE                           # MIT 许可证
├── README.md                         # 项目说明
└── CHANGELOG.md                      # 变更日志
```

---

## 核心模块

### 1. 主控制模块（main.py）

**职责**:
- 命令行参数解析
- 流程编排和调度
- 模式选择（1/2/3三种模式）
- 错误处理和日志

**主要函数**:

```python
def main():
    """主入口函数"""
    # 1. 解析命令行参数
    args = parse_arguments()

    # 2. 交互式模式选择（如需要）
    # 模式1: CLI全程模式（免费）
    # 模式2: CLI+Gemini混动模式
    # 模式3: Gemini增强模式（推荐）
    insights_mode = select_insights_mode(args)

    # 3. 加载数据
    df = load_reviews(args.input_file)

    # 4. AI 打标分析
    tagged_df = analyze_reviews(df, args)

    # 5. 生成用户画像
    personas = analyze_personas(tagged_df)

    # 6. 生成洞察报告
    insights = generate_insights(tagged_df, personas, args)

    # 7. 生成可视化报告
    generate_html_report(tagged_df, personas, insights, args)

    # 8. 保存输出
    save_outputs(tagged_df, insights, args)
```

---

### 2. 配置管理模块（src/config.py）

**职责**:
- 全局配置管理
- 环境变量读取
- 默认值设置

**核心配置**:

```python
# ==================== 数据处理配置 ====================
MAX_REVIEWS: int = 500              # 最大处理评论数
BATCH_SIZE: int = 30                # 批次大小
MAX_CONCURRENT_WORKERS: int = 10    # 最大并发数

# ==================== AI 分析配置 ====================
# CLI 模式
CLAUDE_CLI_CMD: str = "claude"      # Claude CLI 命令

# Gemini 模式
# 模式2: CLI+Gemini混动模式（看板专用）
GEMINI_HTML_MODEL: str = "gemini-3.1-pro-preview"

# 模式3: Gemini增强模式（报告+看板）
GEMINI_INSIGHTS_MODEL: str = "gemini-3-flash-preview"
GEMINI_HTML_MODEL: str = "gemini-3.1-pro-preview"
GEMINI_TEMPERATURE: float = 0.7
GEMINI_MAX_TOKENS: int = 8192

# ==================== 输出配置 ====================
OUTPUT_DIR: str = "output"          # 输出目录
CSV_ENCODING: str = "utf-8-sig"     # CSV 编码
```

---

### 3. 数据加载模块（src/data_loader.py）

**职责**:
- CSV/Excel 文件读取
- 数据验证和清洗
- 列名模糊匹配

**主要功能**:

```python
def load_data(file_path: str) -> pd.DataFrame:
    """
    加载评论数据

    支持格式:
    - CSV (.csv)
    - Excel (.xlsx, .xls)

    自动匹配列名:
    - 评论内容: 内容/评价/body/review
    - 评分: 打分/rating/score
    - 时间: 时间/date/日期
    """
    # 1. 检测文件格式
    # 2. 读取数据
    # 3. 列名匹配
    # 4. 数据验证
    # 5. 返回 DataFrame
```

---

### 4. AI 分析引擎（src/review_analyzer.py）

**职责**:
- AI 打标分析
- 批量并发处理
- CLI/Gemini 调用

**核心流程**:

```python
def analyze_reviews(df: pd.DataFrame, args) -> pd.DataFrame:
    """
    AI 打标分析主函数

    流程:
    1. 数据分批
    2. 并发调用 AI
    3. 结果合并
    4. 数据保存
    """
    # 1. 准备批次
    batches = create_batches(df, batch_size=30)

    # 2. 并发处理
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(analyze_batch, batch) for batch in batches]
        results = [future.result() for future in futures]

    # 3. 合并结果
    tagged_df = pd.concat(results)

    return tagged_df
```

**AI 调用方式**:

```python
def analyze_batch(batch: pd.DataFrame) -> pd.DataFrame:
    """
    批量分析（使用 CLI 模式）

    通过 subprocess 调用 Claude CLI
    """
    prompt = build_prompt(batch)
    cmd = ["claude", prompt]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return parse_result(result.stdout)
```

---

### 5. 用户画像模块（src/user_persona_analyzer.py）

**职责**:
- 识别核心用户群体
- 生成立体化画像
- 选择代表性评论

**四位一体 VOC 系统**:

```python
def analyze_personas(df: pd.DataFrame) -> List[Persona]:
    """
    生成四位一体用户画像

    返回:
    - 核心用户画像
    - 潜在用户画像
    - 流失用户画像
    - 批评用户画像

    每个画像包含:
    - 基本信息（年龄、性别、职业）
    - 使用场景
    - 满意点
    - 痛点
    - 代表性评论
    """
    # 1. 聚类分析
    clusters = cluster_users(df)

    # 2. 识别画像
    personas = identify_personas(clusters)

    # 3. 选择样本
    samples = select_representative_reviews(personas, df)

    return personas
```

---

### 6. 洞察生成模块（src/insights_generator.py）

**职责**:
- 生成深度洞察报告
- 支持三模切换
- 结构化输出

**三模分发器**:

```python
def generate_insights(df: pd.DataFrame, personas: List[Persona], mode: str) -> str:
    """
    洞察生成分发器

    模式:
    - mode=1: CLI 深度模式（全程CLI）
    - mode=2: 混动模式（CLI打标 + Gemini看板）
    - mode=3: Gemini 增强模式（全程Gemini）
    """
    prompt = build_insights_prompt(df, personas)

    if mode == "3":
        return generate_via_gemini(prompt, model='gemini-3-flash-preview')
    else:
        return generate_via_cli(prompt)

def generate_via_gemini(prompt: str, model: str = 'gemini-3-flash-preview') -> str:
    """使用 Gemini API 生成洞察"""
    genai.configure(api_key=GEMINI_API_KEY)
    gen_model = genai.GenerativeModel(model)
    response = gen_model.generate_content(prompt)
    return response.text

def generate_via_cli(prompt: str) -> str:
    """使用 Claude CLI 生成洞察"""
    cmd = ["claude", prompt]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

---

### 7. 报告生成模块（src/report_generator.py）

**职责**:
- HTML 可视化报告生成
- Markdown 洞察报告生成
- CSV 数据导出

**HTML 报告生成**:

```python
def generate_html_report(df: pd.DataFrame, personas: List[Persona], insights: str, args):
    """
    生成黑金奢华 HTML 看板

    功能:
    - KPI 卡片
    - 6 个交互式图表
    - 6 套 3D 头像
    - 鎏金渐变署名
    """
    # 1. 准备数据
    kpi_data = calculate_kpi(df)
    chart_data = prepare_chart_data(df)

    # 2. 加载模板
    template = load_template("assets/report.html")

    # 3. 渲染报告
    html = template.render(
        kpi=kpi_data,
        charts=chart_data,
        personas=personas,
        insights=insights,
        creator=args.creator
    )

    # 4. 保存文件
    save_html(html, args)
```

---

## 数据流程

### 完整处理流程

```
┌──────────────────┐
│  1. 输入数据      │
│  CSV/Excel 文件   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  2. 数据加载      │
│  - 文件读取       │
│  - 列名匹配       │
│  - 数据验证       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  3. AI 打标分析   │
│  - 数据分批       │
│  - 并发调用       │
│  - 标签提取       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  4. 用户画像      │
│  - 聚类分析       │
│  - 画像识别       │
│  - 样本选择       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  5. 洞察生成      │
│  - CLI/Gemini    │
│  - 深度分析       │
│  - 报告生成       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  6. 报告生成      │
│  - CSV 数据       │
│  - Markdown 洞察 │
│  - HTML 看板     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  7. 输出文件      │
│  output/ 目录     │
└──────────────────┘
```

---

## AI 引擎

### 三模架构

```
                    ┌─────────────────┐
                    │  洞察生成请求     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   模式选择器      │
                    │  (1/2/3)        │
                    └────────┬────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │                      │                      │
┌─────▼─────┐        ┌──────▼──────┐        ┌──────▼──────┐
│ 模式1:     │        │ 模式2:        │        │ 模式3:        │
│ CLI全程模式 │        │ 混动模式       │        │ Gemini增强    │
│            │        │ CLI+Gemini    │        │              │
│ - 打标:CLI │        │ - 打标:CLI     │        │ - 打标:Gemini │
│ - 报告:CLI │        │ - 报告:CLI     │        │ - 报告:Gemini │
│ - 看板:本地 │        │ - 看板:Gemini  │        │ - 看板:Gemini │
│ - 免费使用  │        │ - Flash/Pro   │        │ - Flash/Pro   │
└────────────┘        │ - 需API Key    │        │ - 需API Key   │
                      └───────────────┘        └───────────────┘
```

### 三种模式详细说明

#### 模式 1: Claude CLI 模式（全程CLI）
- **打标**: 使用 Claude Code CLI 内置模型
- **洞察报告**: 使用 Claude Code CLI 内置模型
- **可视化看板**: 本地模板渲染（黑金看板）
- **成本**: 消耗 Claude 配额，无 API 费用
- **优势**: 全程免费，深度推理质量高
- **适用**: 个人分析、预算有限、关键决策

#### 模式 2: CLI+Gemini 混动模式
- **打标**: 使用 Claude Code CLI 内置模型
- **洞察报告**: 使用 Claude Code CLI 内置模型
- **可视化看板**: 使用 Gemini 3.1 Pro API
- **成本**: 消耗 Claude 配额 + Gemini API 费用
- **优势**: 兼顾 CLI 深度与 Gemini 高质量看板
- **适用**: 需要高质量可视化看板的场景

#### 模式 3: Gemini 增强模式（推荐）
- **打标**: 使用 Gemini 3.1 Flash API
- **洞察报告**: 使用 Gemini 3.1 Flash API
- **可视化看板**: 使用 Gemini 3.1 Pro API
- **成本**: 仅消耗 Gemini API 费用
- **优势**: 高质量快速分析，推理质量极大增强
- **适用**: 批量分析、追求速度与质量平衡

### AI 调用方式对比

| 特性 | 模式1: CLI全程 | 模式2: 混动模式 | 模式3: Gemini增强 |
|------|--------------|---------------|-----------------|
| **打标引擎** | Claude CLI | Claude CLI | Gemini 3.1 Flash |
| **报告引擎** | Claude CLI | Claude CLI | Gemini 3.1 Flash |
| **看板引擎** | 本地模板 | Gemini 3.1 Pro | Gemini 3.1 Pro |
| **调用方式** | subprocess | subprocess + API | HTTP API |
| **速度** | 中等（~2-5 分钟） | 中等（~2-4 分钟） | 快速（~1-3 分钟） |
| **成本** | Claude 配额 | Claude配额 + API费用 | API 费用 |
| **质量** | 深度高质量 | 混合高质量 | 高质量快速 |
| **并发** | 高（10 并发） | 高（10 并发） | 中（受 API 限制） |
| **API Key** | 不需要 | 需要 | 需要 |

---

## 标签体系

### 22 维度标签架构

```yaml
标签体系:
  人群维度 (4):
    - 性别: [男, 女, 不明]
    - 年龄段: [18-24, 25-34, 35-44, 45-54, 55+]
    - 职业: [学生, 上班族, 自由职业, 退休, 其他]
    - 购买角色: [自用, 送礼, 代购]

  场景维度 (1):
    - 使用场景: [居家, 办公, 户外, 旅行, 其他]

  功能维度 (2):
    - 满意度: [非常满意, 满意, 一般, 不满意, 非常不满意]
    - 具体功能: [功能1, 功能2, 功能3, ...]

  质量维度 (3):
    - 材质: [优质, 一般, 较差]
    - 做工: [精细, 一般, 粗糙]
    - 耐用性: [耐用, 一般, 易损]

  服务维度 (5):
    - 发货速度: [很快, 快, 一般, 慢, 很慢]
    - 包装质量: [完好, 一般, 破损]
    - 客服响应: [及时, 一般, 迟缓]
    - 退换货: [需要, 不需要]
    - 保修: [提及, 未提及]

  体验维度 (4):
    - 舒适度: [很舒适, 舒适, 一般, 不舒适]
    - 易用性: [简单, 一般, 复杂]
    - 外观设计: [很喜欢, 喜欢, 一般, 不喜欢]
    - 价格感知: [很便宜, 便宜, 合理, 偏贵, 很贵]

  市场维度 (2):
    - 竞品对比: [优于竞品, 相当, 不如竞品]
    - 复购意愿: [肯定会, 可能会, 不会]

  情感维度 (1):
    - 总体评价: [正面, 中性, 负面]
```

### 标签生成流程

```
┌─────────────────┐
│  原始评论数据     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  提示词模板       │
│  - 标签定义       │
│  - 示例引导       │
│  - 输出格式       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI 模型推理      │
│  - Claude CLI    │
│  - Gemini API    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  结构化标签       │
│  - JSON 格式     │
│  - 验证和清洗     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CSV 输出        │
│  22 维度标签      │
└─────────────────┘
```

---

## 报告生成

### 报告类型

#### 1. CSV 数据报告

**内容**:
- 原始评论数据
- 22 维度标签
- 元数据（时间、评分等）

**用途**:
- 数据分析
- 二次处理
- BI 工具集成

#### 2. Markdown 洞察报告

**内容**:
- 核心用户画像（4 位一体）
- 产品优势与不足
- 高频关键词
- 改进建议

**用途**:
- 产品优化
- 营销策略
- 团队分享

#### 3. HTML 可视化看板

**内容**:
- KPI 卡片
- 6 个交互式图表
- 6 套 3D 头像
- 鎏金渐变署名

**技术栈**:
- Jinja2 模板引擎
- Chart.js 图表库
- CSS3 动画
- 响应式设计

**特点**:
- 黑金奢华主题
- 高管汇报级别
- 交互式数据展示

---

## 技术栈

### 核心技术

| 类别 | 技术 | 用途 |
|------|------|------|
| **语言** | Python 3.9+ | 主要开发语言 |
| **数据处理** | pandas | 数据分析和处理 |
| **模板引擎** | Jinja2 | HTML 报告生成 |
| **AI 引擎** | Claude CLI | CLI 模式 AI 推理 |
| **AI 引擎** | Gemini API | Gemini 模式 AI 推理 |
| **并发** | concurrent.futures | 多线程并发处理 |
| **可视化** | Chart.js | 交互式图表 |
| **配置** | python-dotenv | 环境变量管理 |

### 依赖包

**核心依赖** (`requirements.txt`):

```
pandas>=2.0.0
jinja2>=3.1.0
python-dotenv>=1.0.0
openpyxl>=3.0.0
google-generativeai>=0.3.0
```

**开发依赖**（可选）:

```
pytest>=7.0.0
black>=23.0.0
flake8>=6.0.0
```

---

## 扩展指南

### 添加新的标签维度

1. 编辑 `references/tag_system.yaml`
2. 更新 `src/prompts/templates.py` 中的提示词
3. 测试验证

### 集成新的 AI 模型

1. 在 `src/insights_generator.py` 中添加新的生成函数
2. 更新配置 `src/config.py`
3. 添加命令行参数支持

### 自定义报告模板

1. 复制 `assets/report.html`
2. 修改样式和布局
3. 更新渲染逻辑

### 添加新的数据源

1. 在 `src/data_loader.py` 中添加新的加载函数
2. 支持新的文件格式
3. 数据验证和转换

---

## 性能优化

### 并发处理

```python
# 默认配置
MAX_CONCURRENT_WORKERS = 10
BATCH_SIZE = 30

# 高性能配置
MAX_CONCURRENT_WORKERS = 20
BATCH_SIZE = 50
```

### 内存优化

```python
# 分批处理
for batch in pd.read_csv('large_file.csv', chunksize=1000):
    process_batch(batch)
```

### 缓存机制

```python
# 缓存 AI 结果
from functools import lru_cache

@lru_cache(maxsize=1000)
def analyze_review_cached(review: str) -> dict:
    return analyze_review(review)
```

---

## 安全性

### API Key 管理

- ✅ 使用环境变量
- ✅ .env 文件不提交到 Git
- ✅ 定期轮换密钥

### 数据隐私

- ✅ 本地处理，数据不上传
- ✅ 支持数据脱敏
- ✅ 符合 GDPR 要求

### 代码安全

- ✅ 输入验证
- ✅ 错误处理
- ✅ 依赖项检查

---

## 最佳实践

### 开发工作流

1. 使用虚拟环境
2. 编写单元测试
3. 代码审查
4. 文档更新

### 部署建议

1. Docker 容器化
2. CI/CD 集成
3. 监控和日志
4. 备份策略

---

## 贡献指南

欢迎贡献代码和改进建议！

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

---

**文档版本**: v1.0.0

**最后更新**: 2026-03-02

**作者**: Buluu@新西楼

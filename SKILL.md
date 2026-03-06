---
name: review-analyzer-skill
description: |
  AI驱动的电商评论深度分析工具,支持CLI本地模式和Gemini增强模式。提供22维度智能标签、黑金奢华可视化看板、四位一体VOC系统(6套3D头像)。



  触发词使用场景:
  - 用户需要分析电商产品评论(Amazon/eBay/AliExpress等)
  - 用户想要生成产品洞察报告和机会点分析
  - 用户需要从评论中提取用户画像和VOC
  - 用户需要创建专业的可视化分析看板
  - 用户提到"电商评论分析"、"评论分析"、"竞品分析"、"用户洞察"、"VOC分析"等关键词

  核心能力:
  - 双模洞察系统: CLI本地模式(使用内置模型) + Gemini增强模式(API付费)
  - 22维度智能标签系统: 人群/场景/功能/质量/服务/体验/市场/情感
  - 黑金奢华可视化看板: 董事会高管汇报级别HTML报告
  - 四位一体VOC系统: 6套3D头像,立体化用户画像
  - 三位一体输出: CSV标签数据 + Markdown洞察报告 + HTML可视化看板

  强制交互约束(绝对级):
  ❗ 无论任何情况,当用户触发评论分析时,AI Agent 必须先通过 AskUserQuestion 工具依次向用户收集以下三个参数,再执行分析命令:
  1. 分析数量(多少条评论)
  2. AI引擎模式(CLI/混动/Gemini)
  3. 报告署名
  严禁自行填充默认值或猜测用户意图。这是本 Skill 的最高优先级规则。
  如果用户明确表示"都用默认值"或"你决定",才可以使用默认值(100条/模式1/AI Assistant)。

  渐进式披露逻辑:
  1. 首次使用时,引导用户克隆主仓库并安装依赖
  2. 提供清晰的快速开始命令和参数说明
  3. 遇到问题时,引导用户查看主仓库文档
  4. 强调双模洞察系统的成本差异和使用场景

  技术要求:
  - Python 3.9+
  - Claude Code CLI(CLI本地模式必需)
  - Gemini API Key(Gemini增强模式可选)

license: MIT
author: Buluu@新西楼
version: 1.0.0
repository: https://github.com/buluslan/review-analyzer-skill
main_project: https://github.com/buluslan/review-analyzer
---

# Review Analyzer Skill - Claude Code自动化接口

## 简介

Review Analyzer Skill是**E-commerce Review Analyzer**的Claude Code自动化接口,让AI Agent能够直接调用强大的评论分析工具,为用户提供即插即用的电商评论深度分析能力。

**注意**: 本Skill是一个轻量级接口,核心功能在主仓库实现。首次使用时会自动引导安装完整工具。

---

## 快速开始

### 1. 安装主仓库(首次使用必需)

```bash
# 克隆主仓库
git clone https://github.com/buluslan/review-analyzer.git
cd review-analyzer

# 安装Python依赖
pip install -r requirements.txt

# 配置环境变量(可选,仅Gemini模式需要)
cp .env.example .env
# 编辑.env,添加GEMINI_API_KEY(如需使用Gemini增强模式)
```

### 2. 使用 Skill 分析评论

AI Agent 应通过交互式问答收集参数,确保分析符合用户需求。在非交互式环境中可使用命令行参数。

交互式参数收集流程详见下方"执行流程"章节。

```bash
# 命令行参数调用方式(非交互环境使用):
# [推荐] 模式 1: Gemini 增强模式 (高质量分析, 需 API Key)
python scripts/analyze.py path/to/reviews.csv --max-reviews 100 --mode 1 --gemini-key "YOUR_KEY" --creator "AI Assistant"

# 模式 2: 混合模式 (CLI 打标 + Gemini 生成看板, 需 Key)
python scripts/analyze.py path/to/reviews.csv --mode 2 --gemini-key "YOUR_KEY"

# 模式 3: CLI 本地模式 (免费, 使用 Claude Code 内置模型)
python scripts/analyze.py path/to/reviews.csv --mode 3 --creator "AI Assistant"
```

### 命令行参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入 CSV/Excel 文件路径 (必需) | - |
| `--max-reviews` | 需要分析的评论条数上限 | 500 |
| `--mode` | 运行模式: **1** (Gemini增强), **2** (混动模式), **3** (CLI本地) | 1 |
| `--creator` | 报告底部的创作者署名 | AI Assistant |
| `--gemini-key` | Gemini API Key (若模式 2/3 未配置环境变量则需提供) | - |
| `--output` | 自定义结果输出目录 | ./output |

---

## 执行流程

> **❗ 绝对约束: AI Agent 必须先问,后执行。严禁跳过第一步。**
>
> 由于本工具在 AI Agent 子进程中无法使用原生交互式菜单,
> AI Agent 必须通过 AskUserQuestion 工具充当"虚拟交互式菜单",
> 向用户依次收集三个关键参数后,再执行分析命令。
> **任何情况下都不得跳过此步骤。**
>
> **⚠️ 严禁使用 `wc -l` 统计评论数！** 必须以 Python 代码运行后的控制台输出为准。
> CSV 文件中一条评论可能包含换行符，占据多个物理行。`wc -l` 统计的是物理行数，不是评论数。

当用户请求分析评论时,按以下步骤执行:

### 第一步:使用AskUserQuestion收集参数(必须执行,不可跳过)

AI Agent 必须使用 AskUserQuestion 工具依次收集以下参数:

#### Q1:分析数量
```yaml
question: "📦 文件共有 X 条评论,您计划打标分析多少条?"
header: "分析数量"
options:
  - label: "100条 (推荐)"
    description: "平衡速度与质量"
  - label: "300条"
    description: "更全面分析"
  - label: "全部"
    description: "分析所有评论"
```

#### Q2:AI引擎选择
```yaml
question: "🤖 请选择 AI 引擎组合:"
header: "AI模式"
options:
  - label: "1. Gemini增强模式 (推荐)"
    description: "调用Gemini API,使用【Gemini 3.1 flash】生成洞察报告,使用【Gemini 3.1 pro】生成可视化看板(需要API Key,产生费用)"
  - label: "2. Claude CLI+Gemini混动模式"
    description: "文字报告使用Claude Code内置模型,可视化看板使用【Gemini 3.1 pro】生成(需要API Key,产生费用)"
  - label: "3. Claude CLI 本地模式"
    description: "使用您的Claude Code中的内置模型进行打标、推理、报告和看板生成"
```

#### Q2.5:Gemini API Key 确认(仅当用户选择模式1或2时必须执行)

> **❗ 强制规则：选择模式1或2后,必须确认 API Key 可用性。禁止跳过,禁止自动回退。**

如果用户选择了模式1或2,AI Agent **必须**执行以下步骤:

1. **检查 `.env` 文件**中是否已配置 `GEMINI_API_KEY`
2. **如果已配置**: 告知用户"检测到已配置的 Gemini API Key",继续执行
3. **如果未配置**: 必须通过 AskUserQuestion 询问用户:

```yaml
question: "🔑 未检测到 Gemini API Key,请选择:"
header: "API Key 配置"
options:
  - label: "手动输入 API Key"
    description: "请提供您的 Gemini API Key"
  - label: "回退到 Claude CLI 本地模式"
    description: "放弃 Gemini 模式,使用本地模式运行"
```

> **⚠️ 严禁自动静默回退！** 如果 API Key 不可用,必须明确告知用户并让用户做出选择。
> 不允许在用户不知情的情况下自动降级到本地模式。

#### Q3:报告署名
```yaml
question: "✍️ 报告需要个性化署名吗?"
header: "署名"
default: "AI Assistant"
options:
  - label: "使用默认"
    description: "AI Assistant"
```

### 第二步:执行分析(必须在第一步完成后才能执行)

> **⚠️ 严禁跳过第一步！** AI Agent 必须先通过 AskUserQuestion 完成所有问题的收集，
> 然后将用户的回答作为命令行参数传入。严禁自行填写默认值或猜测用户意图。
> 如果用户明确表示"使用默认值"或"你决定"，则使用默认值（100条/模式1/AI Assistant）。
> **如果用户选择了 Gemini 模式但 API Key 不可用，必须让用户手动选择回退，禁止自动回退。**


收集参数后,执行以下命令:

```bash
cd <项目根目录>
python3 main.py "<文件路径>" \
  --max-reviews <数量> \
  --mode <模式> \
  --creator "<署名>" \
  --output-dir ./output
```

**注意**: 由于已通过AskUserQuestion收集了所有参数,命令行参数完整,程序不会启动交互式菜单,直接执行分析。

### 第三步:展示结果

分析完成后,告知用户输出文件位置:
- `评论采集及打标数据_{ASIN}.csv` - 22维度标签数据
- `分析洞察报告_{ASIN}.md` - 深度洞察报告
- `可视化洞察报告_{ASIN}.html` - 可视化看板

---

### 3. 查看分析结果

分析完成后,会在输出目录生成三个文件:

- `评论采集及打标数据_{ASIN}.csv` - 22维度标签数据
- `分析洞察报告_{ASIN}.md` - 深度洞察分析报告
- `可视化洞察报告_{ASIN}.html` - 黑金奢华可视化看板

---

## 双模洞察系统

### CLI本地模式(默认)
- **技术实现**: 直接使用Claude Code内置模型执行
- **成本**: 使用您的Claude配额,不产生额外API费用
- **优势**: 深度推理,高质量洞察,适合关键分析
- **适用场景**: 重要产品分析、深度洞察需求

### Gemini增强模式
- **技术实现**: 使用Gemini API
- **成本**: 需要GEMINI_API_KEY,产生API费用
- **优势**: 增强分析能力,支持更多功能
- **适用场景**: 需要增强分析能力、大批量产品分析

**选择建议**:
- 单个产品或小批量分析 → 使用CLI本地模式
- 大批量产品初步筛选 → 使用Gemini增强模式
- 关键决策支持 → 必须使用CLI本地模式

---

## 22维度智能标签系统

工具提供22个维度的AI智能标签,全面覆盖评论信息:

### 标签维度
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

### 标签体系详情

完整的标签定义和说明,请查看主仓库:
- **标签定义**: `references/tag_system.yaml`
- **标签说明**: 主仓库文档`docs/TAG_SYSTEM.md`

---

## 四位一体VOC系统

### 用户画像识别
工具会自动识别3-4类典型用户画像,例如:
- **实用主义者**: 关注性价比、耐用性
- **品质追求者**: 重视材质、做工、设计
- **科技发烧友**: 关注功能、性能、创新
- **时尚生活家**: 看重外观、体验、社交价值

### 3D头像系统
提供6套3D头像,增强用户画像的视觉表现力:
- 商务精英风
- 休闲生活风
- 技术极客风
- 温馨家庭风
- 银发族专属
- Z世代潮流

每类用户画像配备6条精选评论示例,构建立体化VOC系统。

---

## 黑金奢华可视化看板

生成的HTML报告采用董事会高管汇报级别的黑金奢华设计:

### 视觉特性
- **色彩方案**: 黑色背景 + 金色点缀
- **发光效果**: 鎏金渐变创作者署名
- **交互图表**: 6个Chart.js交互式图表
- **响应式设计**: 支持各种屏幕尺寸

### 图表内容
1. **用户画像分布** - 饼图展示各类用户占比
2. **情感分析趋势** - 折线图展示评分分布
3. **维度标签云** - 词云展示高频标签
4. **功能满意度矩阵** - 热力图展示功能vs满意度
5. **使用场景分布** - 柱状图展示场景频次
6. **市场对比雷达** - 雷达图展示竞品对比

---

## CSV文件格式要求

### 必需列(自动模糊匹配)
- **评论内容**: 内容/评价/body/review
- **评分**: 打分/rating/score

### 可选列
- **时间**: 时间/date/日期
- **标题**: 标题/title/summary
- **用户名**: 用户/user/name

### 示例CSV格式
```csv
内容,打分,时间
这个产品质量很好,值得推荐!,5,2024-01-15
物流很快,包装也很仔细,5,2024-01-14
...
```

**注意**: 工具会自动模糊匹配列名,无需担心列名不完全一致。

---

## 输出文件说明

### 1. CSV标签数据
**文件名**: `评论采集及打标数据_{ASIN}.csv`
**内容**: 原始评论 + 22维度AI标签
**用途**: 数据分析、二次处理、导入BI工具

### 2. Markdown洞察报告
**文件名**: `分析洞察报告_{ASIN}.md`
**内容**:
- 战略机会点分析
- 用户痛点总结
- 产品优化建议
- 市场定位洞察

**用途**: 汇报分享、团队协作、决策支持

### 3. HTML可视化看板
**文件名**: `可视化洞察报告_{ASIN}.html`
**内容**: 黑金奢华交互式看板
**用途**:
- 高管汇报演示
- 客户展示
- 产品评审会
- 市场分析报告

---

## 高级用法

### 自定义标签系统
编辑主仓库的`references/tag_system.yaml`,修改标签定义:
```yaml
tags:
  population:
    - name: "自定义人群标签"
      description: "标签说明"
      options: ["选项1", "选项2", "选项3"]
```

### 调整提示词模板
编辑主仓库的`src/prompts/templates.py`,优化AI分析提示词。

### 自定义HTML模板
编辑主仓库的`assets/report.html`,自定义可视化看板样式。

---

## 常见问题

### Q1: Skill和主仓库是什么关系?
**A**: 本Skill是轻量级的自动化接口,核心分析功能在主仓库`review-analyzer`实现。首次使用时需要克隆主仓库,之后Skill会自动调用主仓库的脚本。

### Q2: CLI模式和Gemini模式如何选择?
**A**:
- **CLI本地模式**: 使用Claude Code内置模型,深度推理,适合重要分析
- **Gemini增强模式**: 需要API Key,增强分析能力,适合大批量分析
- **建议**: 小批量用CLI本地模式,大批量用Gemini增强模式

### Q3: 为什么需要Claude CLI?
**A**: CLI本地模式需要Claude Code内置模型进行AI推理。
```bash
npm install -g @anthropic-ai/claude-code
```

### Q4: 如何获取Gemini API Key?
**A**: 访问[Google AI Studio](https://aistudio.google.com/app/apikey)创建API Key。Gemini模式是可选的,不使用也不影响核心功能。

### Q5: CSV文件格式不符合要求怎么办?
**A**: 工具支持自动模糊匹配列名。只要包含评论内容和评分即可,工具会自动识别列名。

### Q6: 分析速度很慢怎么办?
**A**:
1. 使用Gemini增强模式(`--mode 1` 或 `--mode 2`)
2. 减少分析的评论数量
3. 检查网络连接

---

## 渐进式披露逻辑

### 首次使用流程
1. 检测主仓库是否已安装
2. 如未安装,引导用户克隆并安装依赖
3. 提供清晰的快速开始命令
4. 执行分析并展示结果

### 问题诊断流程
1. 遇到错误时,提供具体错误信息
2. 引导用户查看主仓库文档
3. 提供故障排除建议
4. 必要时引导提交Issue

### 功能扩展引导
1. 基础功能稳定后,介绍高级功能
2. 引导用户探索自定义选项
3. 鼓励用户查看主仓库文档
4. 邀请用户贡献代码和反馈

---

## 技术架构

### Skill结构
```
review-analyzer-skill-ai/
├── SKILL.md                    # 本文件 - Skill定义
├── scripts/                    # AI调用脚本
│   └── analyze.py             # 调用主仓库main.py的桥接脚本
├── references/                 # AI需要的参考文档
│   ├── tag_system.yaml        # 22维度标签定义
│   ├── user_personas.md       # VOC系统说明
│   └── output_format.md       # 输出格式规范
└── assets/                     # 输出资源
    ├── report.html            # HTML报告模板(预览)
    └── avatars/               # 6套3D头像(预览)
```

### 主仓库结构(核心功能)
```
review-analyzer/
├── main.py                     # 主入口
├── src/                        # 核心源代码
│   ├── config.py              # 配置管理
│   ├── data_loader.py         # 数据加载
│   ├── review_analyzer.py     # AI分析引擎
│   ├── user_persona_analyzer.py # 用户画像
│   ├── insights_generator.py  # 洞察生成
│   ├── report_generator.py    # 报告生成
│   └── prompts/               # 提示词模板
├── assets/                     # 静态资源
│   ├── report.html            # HTML模板
│   └── avatars/               # 6套3D头像
├── references/                 # 参考文档
├── docs/                       # 用户文档
└── examples/                   # 示例数据
```

---

## 系统要求

| 要求 | 详情 |
|------|------|
| **操作系统** | macOS / Linux / Windows |
| **Python** | 3.9 或更高版本 |
| **Claude CLI** | Claude Code CLI(必需,用于CLI本地模式) |
| **Gemini API** | Gemini API Key(可选,用于Gemini增强模式) |
| **内存** | 建议 4GB+ |
| **磁盘空间** | 建议 500MB+ |

---

## 使用场景示例

### 场景1: 产品优化
```
用户: "帮我分析这个产品的评论,找出用户痛点"
AI: 使用review-analyzer-skill分析CSV文件
     → 生成22维度标签和用户画像
     → 识别痛点和优化机会
     → 输出可视化报告
```

### 场景2: 竞品分析
```
用户: "分析竞品评论,了解他们的优劣势"
AI: 调用评论分析工具
     → 提取竞品优劣势标签
     → 生成对比洞察
     → 输出战略建议
```

### 场景3: 市场调研
```
用户: "批量分析这10个产品的评论"
AI: 使用Gemini增强模式
     → 批量分析10个产品
     → 生成综合趋势报告
     → 识别市场机会点
```

### 场景4: 用户洞察
```
用户: "深入了解目标用户群体"
AI: 分析评论数据
     → 构建四位一体VOC系统
     → 识别典型用户画像
     → 生成用户洞察报告
```

---

## 性能和成本

### CLI本地模式
- **成本**: 使用Claude配额,无额外API费用
- **速度**: 取决于Claude API响应速度
- **质量**: 深度推理,高质量洞察

### Gemini增强模式
- **成本**: 需要Gemini API Key,产生API费用
- **速度**: 通常较快,具体取决于Gemini API响应
- **质量**: 增强分析能力,适合大批量分析

### 批量分析建议
- **小批量(<10产品)**: 使用CLI本地模式
- **大批量(>50产品)**: 使用Gemini增强模式筛选 + CLI本地模式重点分析
- **中等批量(10-50产品)**: 根据预算和需求灵活选择

---

## 贡献和反馈

### 贡献代码
欢迎提交Pull Request到主仓库!

### 反馈问题
- 在主仓库提交Issue
- 描述问题和复现步骤
- 提供错误日志和环境信息

### 功能建议
- 在主仓库提交Feature Request
- 说明使用场景和需求
- 提供具体的改进建议

---

## 许可证

MIT License - 详见主仓库LICENSE文件

---

## 致谢

- 原始灵感来自[ecommerce-competitor-analyzer](https://github.com/buluslan/ecommerce-competitor-analyzer)
- 感谢Anthropic提供Claude AI
- 感谢Google提供Gemini API

---

## 作者

**Buluu@新西楼**

- GitHub: [@buluslan](https://github.com/buluslan)
- 项目主页: [review-analyzer](https://github.com/buluslan/review-analyzer)
- Skill仓库: [review-analyzer-skill](https://github.com/buluslan/review-analyzer-skill)

---

<div align="center">

**如果这个Skill对您有帮助,请给主仓库一个⭐️**

Made with ❤️ by Buluu@新西楼

</div>

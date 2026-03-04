# 更新日志

本文件记录所有重要变更、新功能和问题修复。

---

## [V1.0] - 2026-03-04

### 🎉 首次正式发布

这是 **Review Analyzer Skill** 的第一个正式发布版本，提供完整的电商评论AI深度分析能力。

---

### ✨ 核心特性

#### 🚀 三种AI引擎模式

本版本提供三种灵活的AI引擎组合，满足不同场景需求：

**[1] Claude CLI 全程模式**
- 调用系统原生指令，全流程使用 Claude Code 内置模型
- 无需配置 API Key
- 使用您的 Claude 月度配额（非 API 额度）
- 适合已有 Claude 订阅的用户

**[2] CLI+Gemini 混动模式**
- 标签挖掘：使用 Claude CLI
- 文字报告：使用 Claude CLI
- 可视化看板：调用 Gemini 3.1 Pro
- 需配置 Gemini API Key
- 平衡质量与成本

**[3] Gemini 增强模式**（推荐）
- 标签挖掘：使用 Claude CLI
- 文字报告：调用 Gemini 3.1 Flash
- 可视化看板：调用 Gemini 3.1 Pro
- 推理质量极大增强
- 需配置 Gemini API Key

#### 🏷 22维度智能标签系统

全面覆盖评论信息的8大维度，共22个标签：

**人群维度（4个）**：性别、年龄段、职业、购买角色

**场景维度（1个）**：使用场景

**功能维度（2个）**：满意度、具体功能

**质量维度（3个）**：材质、做工、耐用性

**服务维度（5个）**：发货速度、包装质量、客服响应、退换货、保修

**体验维度（4个）**：舒适度、易用性、外观设计、价格感知

**市场维度（2个）**：竞品对比、复购意愿

**情感维度（1个）**：总体评价

#### 🎨 黑金奢华可视化看板

- **主题**：Luxury Black & Gold（黑金奢华专业风）
- **视觉**：深邃纯黑背景 + 亮金强调色
- **图表**：6个交互式 Chart.js 图表
  - 评分分布图
  - 情感趋势图
  - 标签云图
  - 用户画像雷达图
  - 时间序列图
  - 维度对比图
- **署名**：鎏金渐变发光创作者署名
- **版式**：董事会高管汇报级别设计

#### 👥 四位一体VOC系统

立体化用户画像，增强社交质感：

- **核心用户画像**：产品的主要用户群体
- **潜在用户画像**：有购买意向但未购买的用户
- **流失用户画像**：不再使用产品的用户
- **批评用户画像**：对产品不满的用户

**特色功能**：
- 6套3D头像（商务/休闲/技术/儿童/银发族/奢华）
- 立体化用户画像
- 增强社交质感
- 代表性评论样本

#### 📊 三位一体输出

| 输出文件 | 格式 | 内容说明 |
|---------|------|----------|
| `评论采集及打标数据_{ASIN}.csv` | CSV | 原始评论 + 22维度标签数据 |
| `分析洞察报告_{ASIN}.md` | Markdown | 深度洞察分析与建议 |
| `可视化洞察报告_{ASIN}.html` | HTML | 黑金奢华可视化看板 |

---

### 📦 技术规格

#### 系统要求

- **操作系统**：macOS / Linux / Windows
- **Python**：3.10 或更高版本（推荐 3.11.x）
- **Claude CLI**：Claude Code CLI（CLI 模式必需）
- **Gemini API**：Gemini API Key（Gemini 模式必需）
- **内存**：建议 4GB+
- **磁盘空间**：建议 500MB+

#### 技术栈

- **语言**：Python 3.10+
- **数据处理**：pandas
- **模板引擎**：Jinja2
- **AI 引擎**：Claude CLI + Gemini API
- **可视化**：Chart.js
- **并发**：concurrent.futures

#### 模块化设计

- **main.py**：主入口和流程编排
- **src/config.py**：全局配置管理
- **src/data_loader.py**：数据加载和验证
- **src/review_analyzer.py**：AI 评论分析引擎
- **src/user_persona_analyzer.py**：用户画像分析器
- **src/insights_generator.py**：洞察报告生成器（支持双模）
- **src/report_generator.py**：可视化报告生成器
- **src/prompts/templates.py**：AI 提示词模板

---

### 🎯 使用场景

#### 场景1：产品优化
分析自己产品的评论，发现用户痛点，优化产品功能和设计。

#### 场景2：竞品分析
分析竞品评论，了解竞争对手的优势和劣势，寻找差异化机会。

#### 场景3：市场调研
批量分析多个产品的评论，了解市场需求、用户偏好和行业趋势。

#### 场景4：用户洞察
深度了解目标用户群体，构建精准用户画像，优化营销策略。

---

### 🔒 安全性

#### 数据隐私
- ✅ 本地处理，评论数据不上传到第三方服务器（CLI 模式）
- ✅ 仅在 Gemini 模式下调用 API
- ✅ 支持数据脱敏
- ✅ 符合 GDPR 要求

#### API Key 管理
- ✅ 使用环境变量存储
- ✅ .env 文件不提交到 Git
- ✅ 定期轮换密钥

---

### 🐛 已知限制

- Gemini 模式需要有效的 API Key
- Gemini 模式需要稳定的网络连接
- 打标阶段固定使用 CLI 模式（设计决策）
- HTML 报告生成需要 Gemini API（可选）

---

### 📚 完整文档

- [QUICKSTART.md](QUICKSTART.md) - 5分钟快速开始
- [PYTHON_UPGRADE.md](PYTHON_UPGRADE.md) - Python升级指南
- [README.md](../README.md) - 项目说明

---

### 🙏 致谢

感谢以下项目和工具：
- [Anthropic Claude](https://www.anthropic.com/) - AI 模型支持
- [Google Gemini](https://ai.google.dev/) - AI API 支持
- [Pandas](https://pandas.pydata.org/) - 数据处理
- [Jinja2](https://jinja.palletsprojects.com/) - 模板引擎
- [Chart.js](https://www.chartjs.org/) - 可视化图表

---

### 📄 许可证

本项目采用 [MIT License](../LICENSE) 开源许可证。

---

### 📞 获取支持

- **GitHub Issues**：[提交问题](https://github.com/buluslan/review-analyzer-skill/issues)
- **GitHub Discussions**：[参与讨论](https://github.com/buluslan/review-analyzer-skill/discussions)
- **文档**：[完整文档](../README.md#文档)

---

## [未来版本]

### V1.1（计划中）
- [ ] 多平台支持（eBay/AliExpress）
- [ ] 更多标签维度
- [ ] 自定义报告模板
- [ ] API 服务模式

### V1.2（计划中）
- [ ] 云端部署版本
- [ ] Web UI 界面
- [ ] 定时任务调度
- [ ] 数据库集成

### V2.0（计划中）
- [ ] 多语言支持
- [ ] 实时分析
- [ ] 机器学习模型
- [ ] 企业级功能

---

**完整更新日志**：[GitHub Releases](https://github.com/buluslan/review-analyzer-skill/releases)

**贡献指南**：[CONTRIBUTING.md](CONTRIBUTING.md)（待添加）

**行为准则**：[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)（待添加）

# 双模洞察系统详细说明

## 系统概述

工具提供两种 AI 洞察引擎，满足不同场景需求：

| 模式 | AI 引擎 | 成本 | 适用场景 |
|------|---------|------|---------|
| **Claude CLI本地模式** | 使用您的Claude Code中的内置模型进行全程任务执行。 | 使用您的 Claude 月度配额（非 API 额度） | 重要分析、深度洞察 |
| **Gemini增强模式（推荐）** | 调用Gemini API，使用【Gemini 3.1 flash】生成洞察报告，使用【Gemini 3.1 pro】生成可视化看板 | 付费（需 API Key） | 大批量分析、快速迭代 |
| **Claude CLI+Gemini混动模式** | 文字报告使用Claude Code内置模型，可视化看板使用【Gemini 3.1 pro】生成可视化看板 | 混合（需 API Key） | 平衡质量和生成速度 |

---

## Claude CLI本地模式

### 技术实现
- 直接使用 Claude Code 内置的 Claude 模型执行
- 通过 `claude` CLI 调用（subprocess）
- 所有分析在本地完成，数据不外传

### 成本
- **费用**: 使用您的 Claude Code 配额
- **无额外 API 费用**
- 受 Claude Code 使用额度限制

### 优势
- ✅ **深度推理**: Claude 模型擅长复杂推理和深度分析
- ✅ **高质量洞察**: 更准确的用户画像和痛点识别
- ✅ **数据隐私**: 数据不离开本地环境
- ✅ **无需配置**: 开箱即用，无需 API Key

### 劣势
- ❌ **速度较慢**: 受 Claude API 响应速度限制
- ❌ **配额限制**: 受 Claude Code 使用额度限制
- ❌ **不适合大批量**: 大量产品分析会耗尽配额

### 适用场景
- ✅ 重要产品的深度分析
- ✅ 关键决策支持分析
- ✅ 需要高质量洞察的场景
- ✅ 数据敏感，不能外传的场景
- ✅ 单个产品或小批量分析

### 使用方式
```bash
python3 main.py "reviews.csv" --max-reviews 100 --mode 3 --creator "AI Assistant"
```

---

## Gemini增强模式（推荐）

### 技术实现
- 使用 Google Gemini API
- Gemini 3.1 Flash 生成洞察报告
- Gemini 3.1 Pro 生成可视化看板

### 成本
- **费用**: 需要 Gemini API Key，按使用量计费
- **参考价格**（以 Google 官方为准）:
  - Gemini 3.1 Flash: 约 $0.00015/1K tokens（输入）
  - Gemini 3.1 Pro: 约 $0.0025/1K tokens（输入）
- 每 100 条评论大约花费：$0.05-$0.15（取决于评论长度）

### 优势
- ✅ **速度快**: 比 CLI 模式快 3-5 倍
- ✅ **无配额限制**: 不受 Claude Code 额度限制
- ✅ **大批量分析**: 适合 50+ 产品的批量分析
- ✅ **成本可控**: 大批量时成本更低

### 劣势
- ❌ **需要 API Key**: 需要提前申请 Gemini API Key
- ❌ **数据外传**: 评论数据会发送到 Google 服务器
- ❌ **洞察深度**: 可能略逊于 Claude 深度推理

### 适用场景
- ✅ 大批量产品初步筛选（50+ 产品）
- ✅ 快速迭代和试错
- ✅ 成本敏感型项目
- ✅ 非关键产品的常规分析
- ✅ 时间紧迫的分析任务

### 使用方式
```bash
# 需要先配置 GEMINI_API_KEY
export GEMINI_API_KEY="your_api_key_here"
# 或在 .env 文件中添加

python3 main.py "reviews.csv" --max-reviews 100 --mode 1 --creator "AI Assistant"
```

---

## Claude CLI+Gemini混动模式

### 技术实现
- **评论打标**: 使用 Claude Code CLI（保证质量）
- **报告生成**: 使用 Gemini Flash（快速生成）
- **看板生成**: 使用 Gemini Pro（高质量可视化）

### 成本
- **混合计费**:
  - 打标阶段：使用 Claude 配额
  - 报告和看板：使用 Gemini API
- **成本介于两者之间**

### 优势
- ✅ **平衡质量和速度**: 关键打标用 Claude，生成用 Gemini
- ✅ **灵活性高**: 可根据需要调整各环节的引擎
- ✅ **最佳实践**: 结合两者优势

### 劣势
- ❌ **配置复杂**: 需要同时配置两个系统
- ❌ **成本计算复杂**: 需要分别计算两部分成本

### 适用场景
- ✅ 中等批量分析（10-50 产品）
- ✅ 需要保证打标质量，但希望加快生成速度
- ✅ 对成本敏感，但不愿牺牲太多质量

### 使用方式
```bash
python3 main.py "reviews.csv" --max-reviews 100 --mode 2 --creator "AI Assistant"
```

---

## 模式选择建议

### 按产品数量

| 产品数量 | 推荐模式 | 原因 |
|---------|---------|------|
| 1-5 个 | CLI 本地模式 | 质量优先，配额足够 |
| 5-20 个 | 混动模式 | 平衡质量和速度 |
| 20-50 个 | Gemini 增强模式 | 速度优先，成本可控 |
| 50+ 个 | Gemini 增强模式 | 唯一可行方案 |

### 按分析目的

| 分析目的 | 推荐模式 | 原因 |
|---------|---------|------|
| 关键决策支持 | CLI 本地模式 | 深度洞察，支持重要决策 |
| 产品迭代改进 | 混动模式 | 保证质量，加快速度 |
| 市场调研筛选 | Gemini 增强模式 | 快速筛选大量产品 |
| 竞品分析 | 混动模式 | 平衡质量和效率 |

### 按预算情况

| 预算情况 | 推荐模式 |
|---------|---------|
| 预算充足 | CLI 本地模式（质量最优） |
| 预算有限 | Gemini 增强模式（成本最低） |
| 预算中等 | 混动模式（性价比高） |

---

## 成本对比（估算）

假设分析 100 条评论，平均每条 50 词：

### CLI 本地模式
- **费用**: $0（使用 Claude 配额）
- **时间**: ~15-20 分钟
- **适用**: 小批量、高质量需求

### Gemini 增强模式
- **费用**: ~$0.10-$0.15
- **时间**: ~5-8 分钟
- **适用**: 大批量、快速需求

### 混动模式
- **费用**: ~$0.05-$0.10（打标用配额，生成用 Gemini）
- **时间**: ~10-12 分钟
- **适用**: 中批量、平衡需求

---

## API Key 配置

### 获取 Gemini API Key

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建新项目或选择现有项目
3. 点击 "Create API Key"
4. 复制 API Key

### 配置方式

**方式 1: 环境变量**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

**方式 2: .env 文件**
```bash
# 在项目根目录或工作目录创建 .env 文件
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

**方式 3: 命令行参数**
```bash
python3 main.py "reviews.csv" --gemini-key "your_api_key_here"
```

---

## 常见问题

### Q: CLI 模式提示 "claude not found"
**A**: 需要安装 Claude CLI：
```bash
npm install -g @anthropic-ai/claude-code
```

### Q: Gemini 模式提示 "API key not found"
**A**: 检查环境变量或 .env 文件是否正确配置

### Q: 可以中途切换模式吗？
**A**: 可以。同一批数据可以用不同模式重新分析，对比结果。

### Q: 哪种模式质量最好？
**A**: CLI 本地模式的洞察深度最好，Gemini 模式的速度最快，混动模式是两者的平衡。

# 常见问题

## 通用问题

### Q1: Skill 和主仓库是什么关系?

**A**: 本 Skill 是一个**开箱即用**的完整工具，所有核心功能都内置在 Skill 目录中。不需要额外克隆主仓库，直接使用 Skill 内置的脚本即可。

### Q2: 首次使用需要安装什么?

**A**: 只需安装 Python 依赖：

```bash
pip install pandas jinja2 google-genai
```

如果使用 Gemini 增强模式，还需要配置 API Key。

### Q3: 支持哪些电商平台?

**A**: 支持所有主流电商平台：
- Amazon (亚马逊)
- eBay
- AliExpress (速卖通)
- Shopee
- Lazada
- 淘宝/天猫
- 京东
- 其他提供 CSV 评论导出的平台

### Q4: CSV 文件格式不符合要求怎么办?

**A**: 工具支持自动模糊匹配列名。只要包含评论内容和评分即可，工具会自动识别列名。

详情见：[CSV 格式要求](csv_format.md)

---

## 分析模式问题

### Q5: CLI 模式和 Gemini 模式如何选择?

**A**:

| 模式 | 适用场景 |
|------|---------|
| **CLI 本地模式** | 重要产品分析、深度洞察需求、小批量（1-5个产品） |
| **Gemini 增强模式** | 大批量分析（50+产品）、快速迭代、成本敏感 |
| **混动模式** | 中等批量（10-50产品）、平衡质量和速度 |

详细对比见：[双模洞察系统](dual_mode_system.md)

### Q6: 为什么需要 Claude CLI?

**A**: CLI 本地模式需要 Claude Code 内置模型进行 AI 推理。如果只使用 Gemini 模式，则不需要 Claude CLI。

### Q7: 如何获取 Gemini API Key?

**A**: 访问 [Google AI Studio](https://aistudio.google.com/app/apikey) 创建 API Key。Gemini 模式是可选的，不使用也不影响核心功能。

---

## 分析结果问题

### Q8: 三种输出文件分别是什么?

**A**:

| 文件 | 内容 | 用途 |
|------|------|------|
| CSV 标签数据 | 原始评论 + 22维度标签 | 数据分析、二次处理、导入 BI 工具 |
| Markdown 洞察报告 | 战略机会点、痛点、优化建议 | 汇报分享、团队协作、决策支持 |
| HTML 可视化看板 | 6 个交互式图表、黑金设计 | 高管汇报、客户展示、产品评审 |

详情见：[输出文件说明](output_format.md)

### Q9: 分析速度很慢怎么办?

**A**:
1. 使用 Gemini 增强模式（`--mode 1`）
2. 减少分析的评论数量
3. 检查网络连接

---

## 技术问题

### Q10: 遇到错误怎么办?

**A**: 首先查看错误信息，然后：
1. 检查输入文件格式是否正确
2. 确认依赖已正确安装
3. 查看故障排除文档：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Q11: 分析过程中断怎么办?

**A**:
1. CLI 模式：重新运行相同命令即可
2. Gemini 模式：重新运行，已分析的部分不会重复计费

### Q12: 可以分析多少条评论?

**A**:
- **CLI 模式**: 受 Claude Code 配额限制，建议单次 ≤ 500 条
- **Gemini 模式**: 理论无上限，建议单次 ≤ 1000 条
- **批量分析**: 可以分批次分析多个文件

---

## 数据隐私问题

### Q13: 评论数据会外传吗?

**A**:
- **CLI 模式**: 数据在本地处理，不会外传
- **Gemini 模式**: 数据会发送到 Google 服务器进行处理
- **混动模式**: 打标在本地，报告生成使用 Gemini

### Q14: 分析结果会被保存吗?

**A**: 分析结果只保存在本地输出目录，不会上传到任何服务器。

---

## 高级功能问题

### Q15: 如何自定义标签系统?

**A**: 编辑 `tag_system.yaml` 文件，添加自定义标签维度。详情见：[tag_system.md](tag_system.md)

### Q16: 如何批量分析多个产品?

**A**: 使用批量分析脚本：

```bash
# 分析目录下的所有 CSV 文件
python3 run_batch.py --input-dir ./reviews --output-dir ./output
```

### Q17: 可以从已打标的 CSV 生成报告吗?

**A**: 可以，使用 `generate_from_tagged.py`：

```bash
python3 generate_from_tagged.py "tagged.csv" --mode 1 --creator "AI Assistant"
```

---

## 成本和费用问题

### Q18: 使用这个工具需要多少费用?

**A**:
- **CLI 模式**: 免费（使用 Claude Code 配额）
- **Gemini 模式**: 按使用量计费，100 条评论约 $0.10-$0.15
- **混动模式**: 介于两者之间

详细成本分析见：[性能和成本](performance.md)

### Q19: 如何控制 Gemini 模式的成本?

**A**:
1. 减少单次分析的评论数量
2. 使用 Gemini Flash（更便宜）
3. 先用少量评论测试，再批量分析

---

## 系统兼容性问题

### Q20: 支持 Windows 吗?

**A**: 支持。工具是跨平台的，支持 Windows、macOS、Linux。

### Q21: Python 版本要求?

**A**: Python 3.9 或更高版本。

### Q22: 需要多大的内存和磁盘空间?

**A**:
- **内存**: 建议 4GB+
- **磁盘空间**: 建议 500MB+

---

## 其他问题

### Q23: 可以分析其他语言的评论吗?

**A**: 目前主要优化中文和英文评论。其他语言可能影响分析质量。

### Q24: 可以分析负面评论吗?

**A**: 可以。工具会分析所有评论，包括正面、中性和负面评论。

### Q25: 如何联系技术支持?

**A**:
- 在 GitHub 提交 Issue: [review-analyzer-skill](https://github.com/buluslan/review-analyzer-skill)
- 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 查看 [ARCHITECTURE.md](ARCHITECTURE.md) 了解技术架构

---

## 仍有问题？

如果以上问答没有解决您的问题，请：

1. 查看 [故障排除文档](TROUBLESHOOTING.md)
2. 查看 [技术架构文档](ARCHITECTURE.md)
3. 在 GitHub 提交 Issue，附上：
   - 错误信息截图
   - 输入文件样例（脱敏）
   - 运行环境信息（操作系统、Python 版本）

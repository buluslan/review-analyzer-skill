# 输出示例说明

本目录包含了运行 `review-analyzer-skill V2.0` 后生成的输出示例。

## 📁 输出文件说明

| 文件 | 格式 | 说明 |
|------|------|------|
| `reviews_labeled_sample.csv` | CSV | 原始评论 + 22维度 AI 标签 + 评分 |
| `insights_report_sample.md` | Markdown | 14章深度洞察报告（V1 格式，仅供参考） |
| `visual_report_sample.html` | HTML | V2.0 可视化看板（premium-gold 主题，11板块） |

> 📄 **[在线查看完整洞察报告示例（飞书文档）](https://my.feishu.cn/docx/GMv7dBzlXo5wblxVaWGclEernib)** — 包含 14 章完整内容 + 飞书白板 mermaid 图表

## 🎨 可视化看板主题

V2.0 提供 6 套主题，可直接在浏览器打开 `visual_report_sample.html` 查看 premium-gold 效果：

| 主题 | 风格 |
|------|------|
| premium-gold | 黑金奢华（默认） |
| dark-tech | 赛博朋克 |
| linear-minimal | 极简蓝白 |
| posthog-analytics | 暖橙分析 |
| stripe-executive | 翡翠企业 |
| warm-editorial | 报纸编辑 |

## 🚀 如何生成自己的输出

```bash
# 基本用法
python3 main.py your_reviews.csv

# 指定模板
python3 main.py your_reviews.csv --template dark-tech

# Sorftime 数据源
python3 main.py --source sorftime --asin B09XYZ123 --site US
```

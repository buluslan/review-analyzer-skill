# 示例数据目录

本目录包含 `review-analyzer-skill` 的示例数据和输出参考。

## 📂 目录结构

```
examples/
├── README.md                    # 本文件
├── reviews_sample.csv          # 输入示例: 10条测试评论数据
└── output_sample/              # 输出示例目录
    ├── README.md               # 输出格式说明
    ├── reviews_labeled_sample.csv       # 打标后的CSV数据
    ├── insights_report_sample.md       # Markdown洞察报告
    └── visual_report_sample.html       # HTML可视化报告
```

## 🎯 快速开始

### 1. 查看输入数据
- `reviews_sample.csv`: 包含10条亚马逊产品评论
- 这是用于快速测试的轻量级数据集

### 2. 运行示例分析
```bash
# 使用示例数据运行分析
python main.py --csv examples/reviews_sample.csv

# 或者使用相对路径
cd examples
python ../main.py --csv reviews_sample.csv
```

### 3. 查看输出结果
运行后,会在 `output/` 目录生成三种格式的报告:
- **CSV格式**: 结构化数据,便于分析
- **Markdown格式**: 易读的文本报告
- **HTML格式**: 交互式可视化报告

## 📖 输出格式详解

查看 [`output_sample/README.md`](output_sample/README.md) 了解:
- 每种输出格式的详细说明
- 使用场景和最佳实践
- 如何解读分析结果

## 💡 提示

- 示例数据仅包含10条评论,适合快速测试
- 实际使用时,建议使用50条以上的评论数据以获得更准确的分析结果
- 你可以参考 `output_sample/` 中的示例来理解输出格式

## 🔗 相关文档

- [项目主README](../README.md)
- [使用指南](../docs/usage.md)
- [数据格式说明](../docs/data_format.md)

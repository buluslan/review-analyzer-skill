# CSV 文件格式要求

## 必需列（自动模糊匹配）

工具会自动识别列名，支持常见的列名变体。

### 评论内容列
支持的列名：
- 内容
- 评价
- body
- review
- comment
- text

### 评分列
支持的列名：
- 打分
- 评分
- rating
- score
- stars
- star_rating

## 可选列

### 时间列
- 时间
- date
- 日期
- created_at
- timestamp

### 标题列
- 标题
- title
- summary
- subject

### 用户名列
- 用户
- user
- username
- author
- reviewer_name

## 示例 CSV 格式

### 最简格式
```csv
内容,打分
这个产品质量很好,值得推荐!,5
物流很快,包装也很仔细,5
```

### 完整格式
```csv
标题,内容,打分,时间,用户
超棒的产品,这个产品质量很好,值得推荐!,5,2024-01-15,user123
包装问题,物流很快,但包装有破损,4,2024-01-14,buyer456
```

### Amazon 导出格式（自动适配）
```csv
Id,ProductId,UserId,ProfileName,HelpfulnessNumerator,HelpfulnessDenominator,Score,Time,Summary,Text
1,B001E4KFG0,A3SGXH7AUHU8GW,delmartian,1,1,5,1303862400,Good Quality Dog Food,I have bought several of the...
```

## 格式兼容性

### 支持的文件格式
- CSV (.csv)
- Excel (.xlsx, .xls)
- TSV (.tsv, .tab)

### 编码支持
- UTF-8（推荐）
- UTF-8 with BOM
- GBK/GB2312（中文）
- Latin-1

### 分隔符自动识别
- 逗号 (,)
- 分号 (;)
- 制表符 (	)
- 竖线 (|)

## 数据质量注意事项

### 评论内容
- 确保评论内容列不为空
- 空评论会被自动跳过
- HTML 标签会被自动清理

### 评分
- 支持 1-5 星评分
- 也支持 1-10、1-100 等其他评分范围（会自动归一化）
- 缺失评分默认为 3 星（中立）

### 特殊字符
- 支持中文、日文、韩文等多语言评论
- 支持表情符号 (Emoji)
- 支持引号、逗号等特殊字符（会自动转义）

## 数据格式问题排查

### 问题：读取失败
- 检查文件编码是否为 UTF-8
- 检查分隔符是否正确
- 确保第一行为列名

### 问题：评论数量不对
⚠️ **禁止使用 `wc -l` 统计评论数**

CSV 文件中一条评论可能包含换行符，占据多个物理行。`wc -l` 统计的是物理行数，不是评论数。

**正确方法**:
```python
import pandas as pd
df = pd.read_csv('reviews.csv')
print(f"评论数量: {len(df)}")
```

### 问题：列名识别失败
- 工具支持模糊匹配，大多数常见列名都能识别
- 如果识别失败，手动重命名列为标准列名
- 参考"必需列"部分的支持列名列表

## 常见数据源导出指南

### Amazon 评论导出
使用第三方工具导出后，直接上传即可。工具会自动适配 Amazon 的列名格式。

### eBay 评论导出
导出为 CSV 格式，确保包含评论内容和评分列。

### AliExpress 评论导出
使用浏览器扩展导出，工具会自动识别列名。

### 自定义数据源
确保至少包含两列：评论内容和评分。其他列为可选。

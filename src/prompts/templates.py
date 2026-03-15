"""
AI Prompt 模板模块

基于 PROMPT_TEMPLATES_V1.md 的 Python 实现
"""

from typing import List, Dict


# ==================== 打标提示词 ====================

TAGGING_PROMPT_SINGLE = """你是一个专业电商评论分析AI。请分析以下亚马逊评论，提取22个维度的标签。

# 输入数据
【评论ID】：{review_id}
【评论标题】：{title}
【评论内容】：{body}
【星级】：{rating}星

# 任务要求
严格按以下JSON格式返回（不要markdown代码块，不要其他文字）：

{{
  "review_id": "{review_id}",
  "sentiment": "强烈推荐/推荐/中立/不推荐/强烈不推荐",
  "info_score": <信息密度评分1-20>,
  "tags": {{
    "人群_性别": "男性/女性/不明",
    "人群_年龄段": "18-25/26-35/36-45/46-55/55+/不明",
    "人群_职业": "根据评论内容推断，如：医疗工作者/体力劳动者/办公室职员/学生/退休人员/教师/司机/其他/不明",
    "人群_购买角色": "自用/礼物/商用/不明",
    "场景_使用场景": "根据评论内容推断，如：家用/办公/户外/运动/开车/旅行/其他",
    "功能_满意度": "超出预期/符合预期/低于预期/未提及",
    "功能_具体功能": "简述用户提到的具体功能点，如：续航能力/防水功能/保暖效果/降噪功能等",
    "质量_材质": "优秀/良好/一般/差/未提及",
    "质量_做工": "精细/一般/粗糙/未提及",
    "质量_耐用性": "耐用/一般/易坏/未提及",
    "服务_发货速度": "快/正常/慢/未提及",
    "服务_包装质量": "完好/一般/破损/未提及",
    "服务_客服响应": "及时/一般/迟缓/未提及",
    "服务_退换货": "顺畅/一般/困难/未提及",
    "服务_保修": "有保修/无保修/未提及",
    "体验_舒适度": "舒适/一般/不适/未提及",
    "体验_易用性": "简单/适中/困难/未提及",
    "体验_外观设计": "满意/一般/不满意/未提及",
    "体验_价格感知": "超值/合理/偏贵/未提及",
    "竞品_竞品对比": "用户提及的竞品品牌名称，如：品牌A/品牌B/品牌C等，如无则填'无'",
    "复购_复购意愿": "会复购/可能/不会/未提及",
    "情感_总体评价": "强烈推荐/推荐/中立/不推荐/强烈不推荐"
  }}
}}

# 评分规则 (info_score)
- 基础分：评论字数 > 50字得1分，> 200字再加2分
- 标签分：每个有效标签（非"未提及"）得1分
- 加分项：
  - 提及竞品：+5分
  - 明确复购意愿：+3分
  - 描述使用场景：+2分

# 注意事项
1. 无依据的标签填"不明"或"未提及"
2. 职业标签、使用场景均需从评论内容中推断，如无明确线索则填"不明"
3. info_score 范围 1-20，反映评论的信息价值密度
4. 只返回纯JSON，不要任何解释文字
"""

TAGGING_PROMPT_BATCH = """你是一个专业电商评论分析AI。请分析以下批量亚马逊评论，为每条提取22个维度的标签。

# 输入数据（共 {batch_size} 条评论）
{reviews_json}

# 任务要求
对每条评论进行分析，返回JSON数组格式，每条评论包含：
- review_id: 原始评论ID
- sentiment: 情感倾向 (强烈推荐/推荐/中立/不推荐/强烈不推荐)
- info_score: 信息密度评分 (1-20)
- tags: 完整22维度标签对象

# 标签体系
{tag_system}

# 输出格式
返回纯JSON数组，不要markdown代码块：
[
  {{"review_id": "...", "sentiment": "...", "info_score": 10, "tags": {{...}}}},
  {{"review_id": "...", "sentiment": "...", "info_score": 8, "tags": {{...}}}},
  ...
]
"""

# 标签体系定义（用于提示词中）
TAG_SYSTEM_TEXT = """
人群维度:
  - 人群_性别: 男性/女性/不明
  - 人群_年龄段: 18-25/26-35/36-45/46-55/55+/不明
  - 人群_职业: 根据评论推断职业（医疗工作者/体力劳动者/办公室职员/学生/退休人员/教师/司机/其他/不明）
  - 人群_购买角色: 自用/礼物/商用/不明

场景维度:
  - 场景_使用场景: 根据评论推断职业，如家用/办公/户外/运动/开车/旅行/其他

功能维度:
  - 功能_满意度: 超出预期/符合预期/低于预期/未提及
  - 功能_具体功能: 具体功能点描述

质量维度:
  - 质量_材质: 优秀/良好/一般/差/未提及
  - 质量_做工: 精细/一般/粗糙/未提及
  - 质量_耐用性: 耐用/一般/易坏/未提及

服务维度:
  - 服务_发货速度: 快/正常/慢/未提及
  - 服务_包装质量: 完好/一般/破损/未提及
  - 服务_客服响应: 及时/一般/迟缓/未提及
  - 服务_退换货: 顺畅/一般/困难/未提及
  - 服务_保修: 有保修/无保修/未提及

体验维度:
  - 体验_舒适度: 舒适/一般/不适/未提及
  - 体验_易用性: 简单/适中/困难/未提及
  - 体验_外观设计: 满意/一般/不满意/未提及
  - 体验_价格感知: 超值/合理/偏贵/未提及

市场维度:
  - 竞品_竞品对比: 竞品品牌或'无'
  - 复购_复购意愿: 会复购/可能/不会/未提及

情感维度:
  - 情感_总体评价: 强烈推荐/推荐/中立/不推荐/强烈不推荐
"""

# ==================== 洞察报告提示词 ====================

INSIGHTS_PROMPT_MD = """# Role
你是一位拥有15年经验的"消费者行为学家"和"首席跨境电商数据分析师"。你擅长通过处理结构化的标签数据和非结构化的文本内容，挖掘市场真相。你的行文风格专业、客观、逻辑严密。

# Input Data

## 数据范围
- 评论总量：{total} 条
- 有效打标：{tagged} 条
- ASIN：{asin}

## 用户画像分析（{personas_count} 个）
{personas_details}

## 统计摘要

### 情感分布
{sentiment_distribution}

### 全维度标签分布（非常重要）
{dimensional_distribution}

### 高频标签 Top 15
{top_tags}

## 黄金样本（按用户画像筛选，共 {samples_count} 条）
{golden_samples}

# Core Principles / 核心原则
1. **数据真实性第一**：报告中的每一项统计数据和结论都必须有原始数据支撑。
2. **严禁过度外推（反幻觉红线）**：如果某个标签维度存在大量“不明”或“未提及”数据（如超过 50%），必须如实反映现状。**绝对禁止**利用极少数已知标签去推算、预测或代表整体分布。有多少算多少。
3. **画像侧写诚实性（Persona Inference）**：在描述人口统计特征（年龄、职业）时，请向读者明确说明：这是**基于用户评论的语义线索和生活场景（如工作提及、家庭成员提及）进行的 AI 画像侧写推断**，而非精确的人口普查统计。
4. **特征显著性要求**：如果某个人群属性或画像的样本量极小且不具特征性，必须诚实陈述其“特征不显著”，严禁强行描述。

# Analysis Framework
请严格按照以下 7 大章节进行深度洞察分析，生成完整的 Markdown 报告：

## 0. 数据统计（Ground Truth 锁定区）
- **核心要求**：必须 **100% 完整复刻** 下方【全维度标签分布】表格中的原始数据。
- **严禁串扰**：绝对禁止将 A 维度的百分比写到 B 维度（例如：严禁因为性别有 98% 不明，就推断年龄也有 98% 属于某区间）。
- **格式要求**：[标签维度]：[类别A]（X人，X%），[类别B]（Y人，Y%）...
- 语义归并原则：发挥AI的语义识别能力，将表达有差异但实际属于同个维度的标签进行合并统计。
- 长尾折叠原则：对于分类极其繁杂的维度，仅详细列出占比最高的 Top 10 类别。其余合并记录为"其他/未知"。
- 统计范围：必须涵盖性别、年龄段、职业、场景、功能满意度、质量维度、体验维度以及总体评价等所有被打标的有效标签。

## 1. 用户画像与主流场景 (Persona Inference)
- 核心用户群体有哪些？（基于性别、年龄、职业的交叉分析）
- 典型使用场景有哪些？
- **【数据披露与定调】**：请在此章节开头开宗明义地说明：“以下受众画像基于具有可识别生活轨迹的样本（约占整体X%）进行的语义侧写推断，其余X%的客群特征不显著”。
- 如果基础人口属性大部分为"不明"，请转而从"使用场景"、"核心痛点"等已被明确验证的标签来刻画，坚决避免进行无依据的人群外推预测。
- **必须引用评论原话支撑**

## 2. 核心卖点与价值验证
- 哪些功能/价值被普遍认可？
- 在"功能满意度"为"超出预期"或"总体评价"为"强烈推荐"的数据中，出现频率最高的标签是什么？
- **必须引用评论原话支撑**

## 3. 核心痛点与负面归因
- 用户最不满意的是什么？
- 根源追溯：不要只说"耐用性差"，要指出具体是哪个部件/功能出了问题
- 严重性评估：区分导致退货的致命伤 vs 可忍受的小瑕疵
- **必须引用评论原话支撑**

## 4. 改进建议与优先级
- 基于痛点分析，提出 3 条具体的改进建议
- 按照问题出现的频率和对购买决策的影响程度进行优先级排序（高/中/低）

## 5. 潜在机会与差异化
- 竞品情报：用户提到了哪些竞品？他们认为我们好在哪里、差在哪里？
- 蓝海发现：是否存在小众但满意度极高的人群？
- **必须引用评论原话支撑**

## 6. 典型用户深度解析
- 从高价值评论样本中提取 1-2 个占比最高或最具代表性的"核心用户画像"
- 针对每个画像，抽取 1-2 条评论进行具体解析，总共输出不少于 4 个评论内容的解析
- 必须包含正面和负面评价，保持分布均匀
- 严格按照以下格式输出本章节内容：

**典型画像**：[年龄段] [性别] [职业] [核心需求]（若前面三个维度大比例为"不明"，请直接用一笔带过，如："某年龄不明职业未知的用户"）

**评价原文**："[保留评论核心内容，过长可适当截断]"

**评论解析**：[1-2句话简评。指出该用户的核心痛点、爽点或具体建议]

## 7. 关键洞察总结
- 约精炼的文字（约150字左右）对整份报告进行总结
- 核心聚焦：基于你的专业判断，指出报告中最值得关注的"亮点"或"风险点"

# Output Format
# Report Structure / 报告结构
请输出完整的 Markdown 报告，结构如下：

# {{ product_name }} 评论深度洞察报告

> ASIN: {{ asin }} | 分析时间: {{ date }} | 样本量: {{ total }} 条

## 洞察总览
[不少于 300 字的全局宏观总结，指出品牌当前所处的阶段与最核心的机会/危机]

## 数据统计
[结构化罗列人群、场景、满意度等核心分布数据]
- **【数据真实性死命令】**：你必须以此处提供的【全维度标签分布】表格为**唯一真理**。
- **禁止脑补**：严禁篡改或掩饰“不明/未提及”的数据比例！如果表格显示某维度不明比例为 69%，你的报告必须写“不明 (69%)”，**绝对禁止**将其归入任何具体的业务类别！
- 对性别、年龄段、职业、场景、功能满意度、质量维度、体验维度以及总体评价等核心标签进行统计
- 应用语义归并原则，合并同类型标签
- 对职业、场景、具体功能等维度只显示 Top 10，其余合并为"其他/未知"
- **【反幻觉红线】**：严禁篡改或掩饰“不明/未提及”的数据比例！例如，如果输入数据显示有 67% 的人群年龄段是“不明”，你的报告必须明确写出“不明（67%）”，**绝对禁止**将其归入任何具体的年龄段！有多少算多少！

## 一、核心用户画像与场景
- **【数据披露（必须原样输出）】**：请在本章节的开头第一行，**必须**写下这句声明：“**说明：以下受众画像基于具有可识别生活轨迹的样本（约占整体X%）进行的语义侧写推断（Persona Inference），其余的客群特征不显著。**”（请用实际已知特征的比例替换X%）。
1. 定量统计与交叉洞察（基于性别、年龄、职业等维度的深度碰撞，基于那少部分能推断出画像的用户，描述其生活场景）
2. 典型画像描述（刻画 2 个极其具象的真实使用场景。注意：严禁使用整段大篇幅文字，必须使用加粗标题+简短列表的结构化形式排版，确保移动端及大屏阅读体验）

## 二、核心卖点与价值验证
1. 满意度归因（用户为什么买？为什么给好评？）
2. 语义挖掘（用户在赞美时的关键词及其背后的心理溢价）

## 三、主要痛点与负面归因
1. 问题分布（按严重程度排序）
2. 根源追溯（是产品设计缺陷、质量控制问题、还是用户预期管理不当？）
3. 严重性评估（哪些问题会导致致命的退货和品牌崩塌？）

## 四、改进建议与优先级
1. 硬件/功能迭代建议（优先级：高/中/低）
2. 软件/服务/预期引导建议
3. 详细执行动作与预期 ROI 分析

## 五、潜在机会与差异化
1. 竞品情报分析（基于评论中出现的竞品对比）
2. 蓝海细分场景发现

## 六、典型用户深度解析 (VOC)
请选取 4 个最具代表性的用户，进行"原文 + 深度背景解析 + 核心需求探测"的连线分析。

对于每个用户，请根据评论风格从以下六类中选出一个最契合的头像类型：
- `male_young` (青年/中年男性)
- `female_young` (青年/中年女性)
- `male_elderly` (老年男性)
- `female_elderly` (老年女性)
- `child_boy` (少男/男童)
- `child_girl` (少女/女童)

**典型画像**：[如：26-35岁 男性 IT程序员]
**头像类型**：[从指定的六个枚举值中选择其一]
**核心需求**：[一句话概括，如：缓解长期久坐的腰部酸痛]
**评价原文**："[评论内容 - 保留核心原话，不得仅显示ID，控制在100字以内]"
**评论解析**：[深入分析该用户的爽点、痛点及隐性商业需求]

[重复上述格式，至少4个评论]

[重复上述格式，至少4个评论]

## 关键洞察总结
[约150字，聚焦最值得关注的亮点或风险点]

# Strategic Data Output (System Only)
为了确保可视化看板的准确性，请在 Markdown 报告的最后，强制输出一个 `<strategic_json>` 块。
该块必须是合法的 JSON，严禁包含任何 Markdown 格式。
**数据密度要求:**
- `moat` 和 `vulnerability` 必须分别包含至少 3 项。
- `desc` 字段必须包含具体的逻辑推导或证据，不少于 50 字。
- `execution_matrix` 必须针对三个时间维度给出具体的、可落地的业务指令。

格式如下：
<strategic_json>
{{
  "moat": [
    {{"title": "护城河1标题", "desc": "非常详尽的背景、数据支撑及优势描述..."}},
    {{"title": "护城河2标题", "desc": "..."}},
    {{"title": "护城河3标题", "desc": "..."}}
  ],
  "vulnerability": [
    {{"title": "软肋1标题", "desc": "深度解析该软肋对品牌的杀伤力..."}},
    {{"title": "软肋2标题", "desc": "..."}},
    {{"title": "软肋3标题", "desc": "..."}}
  ],
  "execution_matrix": [
    {{"urgency": "Immediate", "directive": "指令1", "details": "极其详尽的动作拆解...", "roi": "量化的预期回报..."}},
    {{"urgency": "Short-Term", "directive": "指令2", "details": "...", "roi": "..."}},
    {{"urgency": "Long-Term", "directive": "指令3", "details": "...", "roi": "..."}}
  ]
}}
</strategic_json>
"""

INSIGHTS_PROMPT_TXT = """角色设定
你是一位拥有15年经验的消费者行为学家和首席跨境电商数据分析师。你擅长直接处理包含噪音的原始电商表格数据，具备强大的自然语言处理能力，能够从零散的用户评论中自主提取结构化信息并挖掘市场真相。你的行文风格专业、客观、逻辑严密。

核心原则
1. 数据真实性第一：报告内容必须严格基于下方提供的统计数据和样本。
2. 严禁过度外推：遇到大量不明标签时必须如实反映。禁止利用极少数已知标签去强行代表全局。有多少就是多少。
3. 画像侧写诚实性：在描述人口统计特征时，请向读者说明这是基于用户评论的语义线索进行的 AI 画像侧写推断。

输入数据
评论总量：{total} 条
有效打标：{tagged} 条
ASIN：{asin}

【用户画像分析】（{personas_count} 个）
{personas_details}

【统计数据】
情感分布：
{sentiment_distribution}

【全维度标签分布】（锁定数值使用，严格以此为准）
{dimensional_distribution}

高频标签 Top 15：
{top_tags}

【黄金样本】（{samples_count} 条）
{golden_samples}

任务目标
综合定量估算和定性分析，生成一份结构化的《深度洞察分析报告》。

严格格式约束（极其重要）
1. 绝对禁止使用任何 Markdown 格式符号。不要井号 #，不要星号 *，不要下划线 _，不要代码块。
2. 内部层级禁止使用 Markdown 标题，必须使用“【 】”符号。
3. 列表项仅使用数字（1. 2. 3.）或简单的顿号。
4. 引用用户原话时使用双引号。
5. 这是一个纯文本报告，确保它能直接复制到 TXT 文档中且排版整齐。

分析框架（请严格按以下结构输出）

【标题】
关于XX品牌XX产品的评论深度分析报告

【洞察总览】
本次分析的数据量，及 2-3 句话的全局要点总结（负反馈、改进方向）。

【数据统计】
100% 复刻上面的【全维度标签分布】内容。格式为：【维度】：标签1（人数，占比）、标签2（人数，占比）...

【一、核心用户画像与场景】
1. 定量统计分析
2. 职业与场景的交叉洞察
3. 典型用户描述

【二、核心卖点与价值验证】
1. 满意度归因分析
2. 语义挖掘与优点细节

【三、主要痛点与负面归因】
1. 问题分布情况
2. 根源追溯与定性分析
3. 严重性评估

【四、改进建议与优先级】
1. 硬件/功能迭代建议（优先级：高/中/低）
2. 软件/服务建议

【五、潜在机会与差异化】
1. 竞品情报分析
2. 蓝海细分场景发现

【六、典型用户深度解析】
提取 4 个代表性样本（分布均匀），格式如下：
典型画像：[职业/年龄等] [核心需求]
评价原文："内容"
评论解析：解析痛点或爽点。

【七、关键洞察总结】
150字左右，指出最值得关注的亮点或风险。

【战略数据输出（系统专用）】
必须在最后以 <strategic_json> 块输出合法 JSON（不带任何 Markdown 标记）。格式：
<strategic_json>
{{"moat": [], "vulnerability": [], "execution_matrix": []}}
</strategic_json>
"""

# ==================== 辅助函数 ====================

def get_tagging_prompt_single(review: Dict) -> str:
    """
    获取单条评论打标提示词

    Args:
        review: 单条评论数据，必须包含 review_id, title, body, rating

    Returns:
        格式化后的提示词字符串
    """
    return TAGGING_PROMPT_SINGLE.format(
        review_id=review.get("review_id", ""),
        title=review.get("title", ""),
        body=review.get("body", ""),
        rating=review.get("rating", "")
    )


def get_tagging_prompt_batch(reviews: List[Dict]) -> str:
    """
    获取批量评论打标提示词

    Args:
        reviews: 评论列表

    Returns:
        格式化后的提示词字符串
    """
    import json

    # 简化评论数据，只保留必要字段
    simplified_reviews = []
    for r in reviews:
        simplified_reviews.append({
            "review_id": r.get("review_id", ""),
            "title": r.get("title", ""),
            "body": r.get("body", ""),
            "rating": r.get("rating", "")
        })

    reviews_json = json.dumps(simplified_reviews, ensure_ascii=False, indent=2)

    return TAGGING_PROMPT_BATCH.format(
        batch_size=len(reviews),
        reviews_json=reviews_json,
        tag_system=TAG_SYSTEM_TEXT
    )


def get_insights_prompt_md(
    stats: Dict,
    personas: List[Dict],
    samples: List[Dict],
    asin: str,
    product_name: str = None
) -> str:
    """
    获取洞察报告生成提示词（Markdown格式）

    Args:
        stats: 统计数据
        personas: 用户画像列表
        samples: 黄金样本列表
        asin: 产品ASIN
        product_name: 产品名称（可选）

    Returns:
        格式化后的提示词字符串
    """
    from datetime import datetime
    import ast

    def normalize_tags(tags) -> dict:
        """将 tags 转换为 dict（处理字符串情况）"""
        if isinstance(tags, dict):
            return tags
        if isinstance(tags, str):
            try:
                return ast.literal_eval(tags)
            except (ValueError, SyntaxError):
                return {}
        return {}

    # 格式化用户画像
    personas_details = []
    for i, p in enumerate(personas):
        tags = normalize_tags(p.get('tags', {}))
        detail = f"### 画像 {i+1}: {p['name']} ({p['count']} 条)\n"
        detail += f"标签特征: {', '.join(f'{k}:{v}' for k,v in tags.items() if v)}"
        personas_details.append(detail)
    personas_details = "\n\n".join(personas_details)

    # 格式化情感分布
    sentiment_dist = "\n".join(
        f"- **{s}**: {c} 条 ({c/stats['total']*100:.1f}%)"
        for s, c in stats.get("sentiment", {}).items()
    )

    # 格式化高频标签
    top_tags = "\n".join(
        f"{i+1}. **{t}**: {c} 次"
        for i, (t, c) in enumerate(list(stats.get("top_tags", {}).items())[:15])
    )

    # 格式化全维度数据（改用表格以锁定 AI 数值感知，防止串扰）
    dimensional_stats = stats.get("dimensional_stats", {})
    if not dimensional_stats:
        dimensional_distribution = "无具体维度分布数据"
    else:
        dim_lines = []
        for dim, count_dict in dimensional_stats.items():
            total_dim_count = sum(count_dict.values())
            # 构建该维度的子表格
            table = f"| {dim} 类别 | 人数 | 占比 |\n| :--- | :--- | :--- |\n"
            for val, count in count_dict.items():
                table += f"| {val} | {count} | {count/total_dim_count*100:.1f}% |\n"
            dim_lines.append(table)
        dimensional_distribution = "\n".join(dim_lines)

    # 格式化黄金样本
    samples_details = []
    for i, s in enumerate(samples):
        tags = normalize_tags(s.get('tags', {}))
        sample = f"### 样本 {i+1}\n"
        sample += f"**情感**: {s.get('sentiment', '不明')}\n"
        sample += f"**内容**: {s.get('body', '')[:300]}...\n"
        sample += f"**标签**: {', '.join(f'{k}:{v}' for k,v in tags.items() if v)}"
        samples_details.append(sample)
    golden_samples = "\n\n".join(samples_details)

    return INSIGHTS_PROMPT_MD.format(
        total=stats.get("total", 0),
        tagged=stats.get("tagged", 0),
        asin=asin,
        personas_count=len(personas),
        personas_details=personas_details,
        sentiment_distribution=sentiment_dist,
        dimensional_distribution=dimensional_distribution,
        top_tags=top_tags,
        samples_count=len(samples),
        golden_samples=golden_samples,
        product_name=product_name or asin,
        date=datetime.now().strftime("%Y-%m-%d")
    )


def get_insights_prompt_txt(
    stats: Dict,
    personas: List[Dict],
    samples: List[Dict],
    asin: str,
    product_name: str = None
) -> str:
    """
    获取洞察报告生成提示词（纯文本格式）

    Args:
        stats: 统计数据
        personas: 用户画像列表
        samples: 黄金样本列表
        asin: 产品ASIN
        product_name: 产品名称（可选）

    Returns:
        格式化后的提示词字符串
    """
    import ast

    def normalize_tags(tags) -> dict:
        """将 tags 转换为 dict（处理字符串情况）"""
        if isinstance(tags, dict):
            return tags
        if isinstance(tags, str):
            try:
                return ast.literal_eval(tags)
            except (ValueError, SyntaxError):
                return {}
        return {}

    # 格式化用户画像（纯文本格式，不使用 Markdown）
    personas_details = []
    for i, p in enumerate(personas):
        tags = normalize_tags(p.get('tags', {}))
        detail = f"画像 {i+1}: {p['name']} ({p['count']} 条)\n"
        detail += f"标签特征: {', '.join(f'{k}:{v}' for k,v in tags.items() if v)}"
        personas_details.append(detail)
    personas_details = "\n\n".join(personas_details)

    # 格式化情感分布（纯文本格式）
    sentiment_dist = "\n".join(
        f"- {s}: {c} 条 ({c/stats['total']*100:.1f}%)"
        for s, c in stats.get("sentiment", {}).items()
    )

    # 格式化高频标签（纯文本格式）
    top_tags = "\n".join(
        f"{i+1}. {t}: {c} 次"
        for i, (t, c) in enumerate(list(stats.get("top_tags", {}).items())[:15])
    )

    # 格式化全维度数据（改用表格以锁定 AI 数值感知，防止串扰）
    dimensional_stats = stats.get("dimensional_stats", {})
    if not dimensional_stats:
        dimensional_distribution = "无具体维度分布数据"
    else:
        dim_lines = []
        for dim, count_dict in dimensional_stats.items():
            total_dim_count = sum(count_dict.values())
            # 构建该维度的子表格
            table = f"| {dim} 类别 | 人数 | 占比 |\n| :--- | :--- | :--- |\n"
            for val, count in count_dict.items():
                table += f"| {val} | {count} | {count/total_dim_count*100:.1f}% |\n"
            dim_lines.append(table)
        dimensional_distribution = "\n".join(dim_lines)

    # 格式化黄金样本（纯文本格式）
    samples_details = []
    for i, s in enumerate(samples):
        tags = normalize_tags(s.get('tags', {}))
        sample = f"样本 {i+1}\n"
        sample += f"情感: {s.get('sentiment', '不明')}\n"
        sample += f"内容: {s.get('body', '')[:300]}...\n"
        sample += f"标签: {', '.join(f'{k}:{v}' for k,v in tags.items() if v)}"
        samples_details.append(sample)
    golden_samples = "\n\n".join(samples_details)

    return INSIGHTS_PROMPT_TXT.format(
        total=stats.get("total", 0),
        tagged=stats.get("tagged", 0),
        asin=asin,
        personas_count=len(personas),
        personas_details=personas_details,
        sentiment_distribution=sentiment_dist,
        dimensional_distribution=dimensional_distribution,
        top_tags=top_tags,
        samples_count=len(samples),
        golden_samples=golden_samples
    )

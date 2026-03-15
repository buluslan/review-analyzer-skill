"""
用户画像分析模块

基于标签化评论数据识别用户群体并筛选黄金样本
"""

from typing import List, Dict, Tuple
from collections import Counter
from src.config import config


# 预定义颜色方案（用于前端展示）
PERSONA_COLORS = [
    "#d29922",  # 金色
    "#2d9cdb",  # 蓝色
    "#27ae60",  # 绿色
    "#e74c3c",  # 红色
]

# 情感映射到前端样式类
SENTIMENT_CLASS_MAP = {
    "强烈推荐": "strong-positive",
    "推荐": "positive",
    "中立": "neutral",
    "不推荐": "negative",
    "强烈不推荐": "strong-negative",
}

# 正面情感列表
POSITIVE_SENTIMENTS = ["强烈推荐", "推荐"]

# 负面情感列表
NEGATIVE_SENTIMENTS = ["不推荐", "强烈不推荐"]


def analyze_user_personas(tagged_reviews: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """分析用户画像并筛选代表性样本

    基于「场景_使用场景」+「人群_性别」组合识别用户画像,
    为每个画像筛选高质量的正负面样本。

    Args:
        tagged_reviews: 已打标的评论列表，每条包含:
            - review_id: 评论唯一标识
            - title: 评论标题
            - body: 评论内容
            - rating: 评分 (1-5)
            - sentiment: 情感倾向 (强烈推荐/推荐/中立/不推荐/强烈不推荐)
            - info_score: 信息密度评分 (1-20)
            - tags: 22维度标签字典

        Returns:
            personas: 用户画像列表, 按样本数量降序排列
            golden_samples: 黄金样本列表, 包含各画像的代表性样本

    Example:
        >>> reviews = [
        ...     {
        ...         "review_id": "R001",
        ...         "body": "在家用很方便",
        ...         "rating": 5,
        ...         "sentiment": "强烈推荐",
        ...         "info_score": 18,
        ...         "tags": {"场景_使用场景": "家用", "人群_性别": "女性"}
        ...     },
        ...     # ... 更多评论
        ... ]
        >>> personas, samples = analyze_user_personas(reviews)
        >>> len(personas)
        2
        >>> personas[0]["name"]
        '家用_女性'
    """
    if not tagged_reviews:
        return [], []

    # Step 1: 识别用户画像（场景 + 性别组合）
    personas, dimension_name = _identify_personas(tagged_reviews)

    # Step 2: 为每个画像筛选黄金样本
    golden_samples = _select_golden_samples(tagged_reviews, personas)

    return personas, golden_samples


def _identify_personas(reviews: List[Dict]) -> Tuple[List[Dict], str]:
    """识别用户画像（包含维度退化逻辑）

    Args:
        reviews: 评论列表

    Returns:
        Tuple[画像列表, 使用的维度名称]
    """
    # 逻辑 A: 动态阈值 (小样本下降低门槛)
    total_samples = len(reviews)
    min_count = 2 if total_samples <= 100 else config.PERSONA_MIN_COUNT
    
    # 逻辑 B: 维度退化尝试序列
    # (维度标题, 标签键列表)
    dimension_attempts = [
        ("场景_性别", ["场景_使用场景", "人群_性别"]),
        ("场景", ["场景_使用场景"]),
        ("性别", ["人群_性别"])
    ]

    best_dimension = "全局"
    final_personas_raw = []
    
    for dim_name, tag_keys in dimension_attempts:
        persona_counter = Counter()
        persona_tag_stats = {}

        for review in reviews:
            tags = review.get("tags", {})
            values = [tags.get(k, "不明") for k in tag_keys]
            # 过滤掉全是不明的情况
            if all(v in ["不明", "未提及", "nan", "None"] for v in values):
                continue
            
            p_name = " + ".join(values)
            persona_counter[p_name] += 1
            
            if p_name not in persona_tag_stats:
                persona_tag_stats[p_name] = {}
            for t_key, t_val in tags.items():
                if t_val:
                    if t_key not in persona_tag_stats[p_name]:
                        persona_tag_stats[p_name][t_key] = Counter()
                    persona_tag_stats[p_name][t_key][t_val] += 1

        # 筛选有效画像
        valid = [
            (name, count) for name, count in persona_counter.most_common()
            if count >= min_count
        ]
        
        if valid:
            best_dimension = dim_name
            for idx, (name, count) in enumerate(valid[:config.MAX_PERSONAS]):
                typical_tags = {}
                for t_key, counter in persona_tag_stats.get(name, {}).items():
                    top_val, top_count = counter.most_common(1)[0]
                    # Append the actual exact count of people who had this known tag
                    typical_tags[t_key] = f"{top_val}(仅{top_count}人有此特征)"
                
                final_personas_raw.append({
                    "name": name,
                    "count": count,
                    "tags": typical_tags,
                    "dimension": tag_keys # 保存用于匹配的键
                })
            break

    # 兜底：如果还是没有，创建一个全局画像
    if not final_personas_raw:
        final_personas_raw.append({
            "name": "全量用户",
            "count": len(reviews),
            "tags": {},
            "dimension": []
        })
        best_dimension = "全局综述"

    # 赋予颜色
    for idx, p in enumerate(final_personas_raw):
        p["color"] = PERSONA_COLORS[idx % len(PERSONA_COLORS)]
    
    return final_personas_raw, best_dimension


def _select_golden_samples(
    reviews: List[Dict],
    personas: List[Dict]
) -> List[Dict]:
    """为每个画像筛选黄金样本"""
    if not personas:
        return []

    golden_samples = []
    for persona in personas:
        persona_name = persona["name"]
        dim_keys = persona.get("dimension", [])
        
        # 筛选属于该画像的评论
        reviews_for_persona = []
        for r in reviews:
            if not dim_keys: # 全局画像
                reviews_for_persona.append(r)
                continue
                
            tags = r.get("tags", {})
            r_persona_name = " + ".join([tags.get(k, "不明") for k in dim_keys])
            if r_persona_name == persona_name:
                reviews_for_persona.append(r)

        # 分离并排序
        pos = sorted([r for r in reviews_for_persona if r.get("sentiment") in POSITIVE_SENTIMENTS], 
                     key=lambda x: x.get("info_score", 0), reverse=True)
        neg = sorted([r for r in reviews_for_persona if r.get("sentiment") in NEGATIVE_SENTIMENTS], 
                     key=lambda x: x.get("info_score", 0), reverse=True)

        # 取样 (3正+3负)
        for r in (pos[:3] + neg[:3]):
            sample = {
                "review_id": r.get("review_id"),
                "body": r.get("body", r.get("title", "")),
                "rating": r.get("rating"),
                "sentiment": r.get("sentiment"),
                "sentiment_class": SENTIMENT_CLASS_MAP.get(r.get("sentiment"), "neutral"),
                "info_score": r.get("info_score", 0),
                "tags": r.get("tags", {}),
                "persona_name": persona_name,
            }
            golden_samples.append(sample)

    return golden_samples


def get_persona_summary(personas: List[Dict]) -> str:
    """生成画像摘要文本

    Args:
        personas: 画像列表

    Returns:
        摘要文本
    """
    if not personas:
        return "未识别到有效用户画像（评论样本不足）"

    lines = [
        f"识别到 {len(personas)} 个用户画像：",
        ""
    ]

    for persona in personas:
        lines.append(
            f"- {persona['name']}: {persona['count']} 条评论 "
            f"(占比 {persona['count'] / sum(p['count'] for p in personas) * 100:.1f}%)"
        )

    return "\n".join(lines)


def validate_sample_distribution(golden_samples: List[Dict]) -> Dict[str, int]:
    """验证样本分布

    Args:
        golden_samples: 黄金样本列表

    Returns:
        统计信息字典
    """
    if not golden_samples:
        return {"total": 0, "positive": 0, "negative": 0}

    positive_count = sum(
        1 for s in golden_samples
        if s.get("sentiment") in POSITIVE_SENTIMENTS
    )
    negative_count = sum(
        1 for s in golden_samples
        if s.get("sentiment") in NEGATIVE_SENTIMENTS
    )

    return {
        "total": len(golden_samples),
        "positive": positive_count,
        "negative": negative_count,
        "neutral": len(golden_samples) - positive_count - negative_count,
    }

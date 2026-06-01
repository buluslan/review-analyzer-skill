"""
洞察报告生成模块 V1.0 - CLI 原生版

统一使用 subprocess 调用宿主 CLI 引擎生成洞察报告。
支持 claude / opencode 双引擎，由 config 自动适配。
"""

import json
import logging
import re
import subprocess
from typing import List, Dict, Optional
from collections import Counter
from datetime import datetime

# 模块级缓存：最近一次 strategic_json 数据（供 HTML 看板使用）
_last_strategic_data: Dict = {}

from src.config import config
from src.prompts.templates import get_insights_prompt_md, get_insights_prompt_txt

# 配置日志
logger = logging.getLogger(__name__)


# ==================== 核心函数 ====================

def calculate_stats_summary(tagged_reviews: List[Dict]) -> Dict:
    """计算统计摘要

    统计已打标评论的情感分布、高频标签等信息。

    Args:
        tagged_reviews: 已打标的评论列表，每条包含:
            - sentiment: 情感倾向 (强烈推荐/推荐/中立/不推荐/强烈不推荐)
            - tags: 22维度标签字典
            - rating: 评分 (1-5)

    Returns:
        统计摘要字典:
        {
            "total": 总评论数,
            "tagged": 已打标数,
            "sentiment": {"强烈推荐": 10, "推荐": 50, ...},
            "top_tags": {"人群_性别:男性": 45, ...}
        }

    Example:
        >>> reviews = [
        ...     {"sentiment": "强烈推荐", "tags": {"人群_性别": "男性", "场景_使用场景": "家用"}},
        ...     {"sentiment": "推荐", "tags": {"人群_性别": "女性", "场景_使用场景": "办公"}},
        ... ]
        >>> stats = calculate_stats_summary(reviews)
        >>> stats["sentiment"]["强烈推荐"]
        1
        >>> stats["top_tags"]["人群_性别:男性"]
        1
    """
    if not tagged_reviews:
        return {
            "total": 0,
            "tagged": 0,
            "sentiment": {},
            "top_tags": {}
        }

    total = len(tagged_reviews)
    tagged_count = sum(1 for r in tagged_reviews if r.get("tags"))

    # 1. 统计情感分布
    sentiment_counter = Counter()
    for review in tagged_reviews:
        sentiment = review.get("sentiment", "中立")
        if sentiment:
            sentiment_counter[sentiment] += 1

    sentiment_dist = dict(sentiment_counter)

    # 2. 统计高频标签和全维度分布
    # 格式: "维度_标签名:值" 如 "人群_性别:男性"
    tag_counter = Counter()
    dimensional_stats = {}
    
    # 保持数据完整性：不再过滤"不明"或"未提及"，让大模型看到真实的分布（特别是缺失率）
    # 大模型会根据 Prompt 中的"长尾折叠"和"反幻觉"原则自主处理这些标签
    for review in tagged_reviews:
        tags = review.get("tags", {})
        for tag_key, tag_value in tags.items():
            if tag_value:
                # 扁平化的高频标签
                combined_key = f"{tag_key}:{tag_value}"
                tag_counter[combined_key] += 1
                
                # 结构化的维度打标
                if tag_key not in dimensional_stats:
                    dimensional_stats[tag_key] = Counter()
                dimensional_stats[tag_key][tag_value] += 1

    # 取 Top 30 标签 (供本地和旧看板逻辑使用)
    top_tags = dict(tag_counter.most_common(30))
    
    # 将 Counter 转换为普通 dict (供全面数据使用)
    for dim in dimensional_stats:
        dimensional_stats[dim] = dict(dimensional_stats[dim].most_common(50)) # 取每个维度前50防止过大

    # 3. 计算平均评分
    ratings = [r.get("rating", 0) for r in tagged_reviews if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    return {
        "total": total,
        "tagged": tagged_count,
        "sentiment": sentiment_dist,
        "top_tags": top_tags,
        "dimensional_stats": dimensional_stats,
        "avg_rating": avg_rating
    }


def generate_insights(
    stats: Dict,
    personas: List[Dict],
    golden_samples: List[Dict],
    asin: str,
    product_name: str = None
) -> str:
    """生成洞察报告（分发器）

    根据 config 构建提示词，统一使用 CLI 引擎生成

    Args:
        stats: 统计摘要，来自 calculate_stats_summary()
        personas: 用户画像列表，来自 analyze_user_personas()
        golden_samples: 黄金样本列表，来自 analyze_user_personas()
        asin: 产品ASIN
        product_name: 产品名称（可选）

    Returns:
        Markdown 格式的洞察报告字符串。
        失败时返回空字符串。

    Example:
        >>> stats = {"total": 100, "tagged": 95, "sentiment": {...}, "top_tags": {...}}
        >>> personas = [{"name": "家用_女性", "count": 30, "tags": {...}}]
        >>> samples = [{"body": "很棒的产品", "sentiment": "强烈推荐", ...}]
        >>> report = generate_insights(stats, personas, samples, "B08X", "测试产品")
        >>> "评论深度洞察报告" in report
        True
    """
    # V2.0 优先使用新的 Prompt 管理器（数据预处理 + 14 章结构）
    try:
        from src.prompts.manager import build_insights_prompt as _build_v2_prompt

        # 构建 V2 prompt（含数据预处理、噪声过滤、分层注入）
        context = {}
        # 检查是否有日期数据 → 启用时间趋势章节
        has_date = any(
            r.get("date") and r.get("date") not in ("", "nan", "None")
            for r in golden_samples
        )
        if has_date:
            context["has_review_date"] = True
            context["time_distribution_text"] = "用户评论包含日期信息，可进行时间趋势分析"

        prompt = _build_v2_prompt(
            stats=stats,
            personas=personas,
            samples=golden_samples,
            asin=asin,
            product_name=product_name,
            context=context,
        )
        logger.info("使用 V2.1 Prompt 管理器（14 章结构 + 数据预处理）")
    except Exception as exc:
        # 降级到 V1 prompt
        logger.warning("V2 Prompt 加载失败，降级到 V1: %s", exc)
        if config.INSIGHTS_FORMAT == "md":
            prompt = get_insights_prompt_md(
                stats=stats,
                personas=personas,
                samples=golden_samples,
                asin=asin,
                product_name=product_name
            )
        else:
            prompt = get_insights_prompt_txt(
                stats=stats,
                personas=personas,
                samples=golden_samples,
                asin=asin,
                product_name=product_name
            )

    # 统一使用 CLI 引擎生成
    report_text = _generate_via_cli(prompt, asin)

    # 兜底：确保必需的 mermaid 图表存在（AI 可能跳过 mermaid 生成）
    if report_text:
        report_text = _ensure_mermaid_charts(report_text, stats, personas)

    # V1.0 优化：剥离 <strategic_json> 标签，确保 Markdown 报告内容纯净
    global _last_strategic_data
    _last_strategic_data = {}
    if report_text and "<strategic_json>" in report_text:
        import re as _re
        # 先提取 strategic_json 供 HTML 看板使用
        _match = _re.search(
            r'<strategic_json>\s*(\{.*?\})\s*</strategic_json>',
            report_text, _re.DOTALL,
        )
        if _match:
            try:
                _last_strategic_data = json.loads(_match.group(1))
            except json.JSONDecodeError:
                pass
        # 再从报告中移除
        report_text = _re.sub(r'<strategic_json>.*?</strategic_json>', '', report_text, flags=_re.DOTALL).strip()

    return report_text


def _generate_via_cli(prompt: str, asin: str) -> str:
    """使用 CLI 引擎生成洞察报告（支持 claude / opencode）"""
    cmd = config.build_cli_cmd(prompt)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=config.CLI_TIMEOUT,
        check=True
    )

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "未知错误"
        logger.error(f"CLI 返回非零状态码: {error_msg}")
        return ""

    report_text = result.stdout.strip()
    if not report_text:
        logger.error("CLI 返回空内容")
        return ""

    logger.info(f"成功生成洞察报告({config.CLI_ENGINE.upper()}): ASIN={asin}, 字数={len(report_text)}")
    return report_text


def generate_insights_with_metadata(
    tagged_reviews: List[Dict],
    personas: List[Dict],
    golden_samples: List[Dict],
    asin: str,
    product_name: str = None
) -> Dict:
    """生成洞察报告及元数据

    便捷函数，一次性完成统计计算和报告生成。

    Args:
        tagged_reviews: 已打标的评论列表
        personas: 用户画像列表
        golden_samples: 黄金样本列表
        asin: 产品ASIN
        product_name: 产品名称（可选）

    Returns:
        {
            "report": Markdown 报告内容,
            "stats": 统计摘要,
            "generated_at": 生成时间
        }
    """
    # 计算统计数据
    stats = calculate_stats_summary(tagged_reviews)

    # 生成洞察报告
    report = generate_insights(
        stats=stats,
        personas=personas,
        golden_samples=golden_samples,
        asin=asin,
        product_name=product_name
    )

    return {
        "report": report,
        "stats": stats,
        "generated_at": datetime.now().isoformat()
    }


# ==================== 辅助函数 ====================

def format_sentiment_distribution(sentiment_dist: Dict[str, int], total: int) -> str:
    """格式化情感分布为可读字符串

    Args:
        sentiment_dist: 情感分布字典
        total: 总评论数

    Returns:
        格式化的字符串，如 "- **强烈推荐**: 10 条 (10.0%)"
    """
    lines = []
    for sentiment, count in sentiment_dist.items():
        percentage = (count / total * 100) if total > 0 else 0
        lines.append(f"- **{sentiment}**: {count} 条 ({percentage:.1f}%)")
    return "\n".join(lines)


def format_top_tags(top_tags: Dict[str, int], limit: int = 15) -> str:
    """格式化高频标签为可读字符串

    Args:
        top_tags: 高频标签字典
        limit: 显示数量限制

    Returns:
        格式化的字符串，如 "1. **人群_性别:男性**: 45 次"
    """
    lines = []
    for i, (tag, count) in enumerate(list(top_tags.items())[:limit]):
        lines.append(f"{i+1}. **{tag}**: {count} 次")
    return "\n".join(lines)


def validate_stats(stats: Dict) -> bool:
    """验证统计数据的完整性

    Args:
        stats: 统计摘要字典

    Returns:
        True if valid, False otherwise
    """
    required_keys = {"total", "tagged", "sentiment", "top_tags"}
    return required_keys.issubset(stats.keys())


def get_sentiment_percentage(stats: Dict, sentiment: str) -> float:
    """获取特定情感的占比

    Args:
        stats: 统计摘要字典
        sentiment: 情感类别

    Returns:
        百分比 (0-100)
    """
    total = stats.get("total", 0)
    if total == 0:
        return 0.0

    sentiment_count = stats.get("sentiment", {}).get(sentiment, 0)
    return (sentiment_count / total) * 100


def get_top_persona(personas: List[Dict]) -> Dict:
    """获取样本量最大的用户画像

    Args:
        personas: 用户画像列表

    Returns:
        画像字典，如果没有则返回 None
    """
    if not personas:
        return None

    return max(personas, key=lambda p: p.get("count", 0))


def summarize_stats(stats: Dict) -> str:
    """生成统计摘要的一行描述

    Args:
        stats: 统计摘要字典

    Returns:
        摘要字符串，如 "共 100 条评论，其中强烈推荐 40%"
    """
    total = stats.get("total", 0)
    tagged = stats.get("tagged", 0)

    parts = [f"共 {total} 条评论"]

    if total > 0:
        # 找出最多的情感
        sentiment_dist = stats.get("sentiment", {})
        if sentiment_dist:
            top_sentiment = max(sentiment_dist, key=sentiment_dist.get)
            top_pct = get_sentiment_percentage(stats, top_sentiment)
            parts.append(f"{top_sentiment} {top_pct:.0f}%")

    return "，".join(parts) + "。"


def get_last_strategic_data() -> Dict:
    """获取最近一次 generate_insights() 调用提取的 strategic_json 数据。

    供 HTML 看板模板使用：strategy、execution_matrix、top_pain_points 等。
    在 generate_insights() 调用之后、报告剥离 <strategic_json> 之前提取。

    Returns:
        strategic_json 字典，可能为空。
    """
    return _last_strategic_data


# ==================== Mermaid 兜底机制 ====================

def _ensure_mermaid_charts(report_text: str, stats: Dict, personas: List[Dict]) -> str:
    """确保报告中包含必需的 mermaid 图表，缺失时从数据自动生成。

    检查报告中 4 个关键章节是否包含对应的 mermaid 代码块。
    如果章节标题存在但 mermaid 缺失，则从 stats/personas 数据自动生成并注入。

    Args:
        report_text: AI 生成的洞察报告 Markdown 文本
        stats: 统计摘要数据，来自 calculate_stats_summary()
        personas: 用户画像列表，来自 analyze_user_personas()

    Returns:
        补全 mermaid 后的报告文本（如无缺失则原样返回）
    """
    if not report_text:
        return report_text

    # 定义 4 个必需的 mermaid 图表及其对应的章节
    required_charts = [
        {
            "key": "pain_points_matrix",
            # 匹配第五章「主要痛点与负面归因」的标题
            "heading_patterns": [
                r"#{2,3}\s*.*(?:主要痛点|痛点与负面|痛点.*归因|Pain\s*Point)",
            ],
            "mermaid_keywords": ["graph TD", "graph LR"],
            "generator": _generate_pain_points_matrix,
        },
        {
            "key": "competitor_mindmap",
            # 匹配第七章「潜在机会与差异化」的标题
            "heading_patterns": [
                r"#{2,3}\s*.*(?:潜在机会|差异化|竞品|Opportunit|Differentiat)",
            ],
            "mermaid_keywords": ["mindmap"],
            "generator": _generate_competitor_mindmap,
        },
        {
            "key": "topic_mindmap",
            # 匹配第十一章「关键词与话题聚类」的标题
            "heading_patterns": [
                r"#{2,3}\s*.*(?:关键词|话题聚类|Topic\s*Cluster|Keyword)",
            ],
            "mermaid_keywords": ["mindmap"],
            "generator": _generate_topic_mindmap,
        },
        {
            "key": "action_matrix",
            # 匹配第十三章「行动决策仪表盘」的标题
            "heading_patterns": [
                r"#{2,3}\s*.*(?:行动决策|行动.*仪表盘|Action\s*Dashboard|Decision)",
            ],
            "mermaid_keywords": ["graph TD", "graph LR"],
            "generator": _generate_action_matrix,
        },
    ]

    injected_count = 0
    for chart_config in required_charts:
        # 找到章节标题的位置
        heading_match = _find_heading_match(report_text, chart_config["heading_patterns"])
        if not heading_match:
            # 章节标题不存在，跳过（AI 可能没有输出该章节）
            continue

        # 检查该章节标题后面是否已经有 mermaid 代码块
        heading_end = heading_match.end()
        # 查找下一个同级或更高级标题的位置（章节边界）
        next_heading_pos = _find_next_heading_pos(
            report_text, heading_match.start(), heading_match.group(0)
        )

        section_text = report_text[heading_end:next_heading_pos]

        # 检查该章节中是否已存在 mermaid 代码块且包含对应关键词
        has_mermaid = bool(re.search(r"```mermaid", section_text))
        if has_mermaid:
            # 已有 mermaid，检查是否包含预期的关键词
            has_expected_content = any(
                kw in section_text for kw in chart_config["mermaid_keywords"]
            )
            if has_expected_content:
                continue  # mermaid 完好，无需兜底

        # 需要兜底：生成 mermaid 并注入
        mermaid_block = chart_config["generator"](stats, personas)
        if mermaid_block:
            report_text = _inject_mermaid_after_heading(
                report_text, heading_match, mermaid_block
            )
            injected_count += 1
            logger.info("Mermaid 兜底注入: %s", chart_config["key"])

    if injected_count > 0:
        logger.info("Mermaid 兜底完成: 共注入 %d 个图表", injected_count)

    return report_text


def _find_heading_match(
    text: str, patterns: List[str]
) -> Optional[re.Match]:
    """在文本中查找第一个匹配的章节标题。

    Args:
        text: 报告全文
        patterns: 正则表达式列表，用于匹配章节标题

    Returns:
        第一个匹配的 re.Match 对象，未找到返回 None
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match
    return None


def _find_next_heading_pos(text: str, current_heading_start: int, current_heading: str) -> int:
    """查找当前章节之后的下一个同级或更高级标题的位置。

    Args:
        text: 报告全文
        current_heading_start: 当前标题在文本中的起始位置
        current_heading: 当前标题的完整匹配文本

    Returns:
        下一章节的起始位置，如果没有下一章节则返回文本末尾位置
    """
    # 从当前标题之后开始搜索
    search_start = current_heading_start + len(current_heading)

    # 匹配 ## 或 ### 开头的标题行
    next_match = re.search(r"\n#{2,3}\s+", text[search_start:])
    if next_match:
        return search_start + next_match.start()
    return len(text)


def _inject_mermaid_after_heading(
    report_text: str, heading_match: re.Match, mermaid_block: str
) -> str:
    """在章节标题之后注入 mermaid 代码块。

    在标题行的下一行插入 mermaid 代码块，标题和 mermaid 之间保留一个空行。

    Args:
        report_text: 报告全文
        heading_match: 章节标题的 re.Match 对象
        mermaid_block: 要注入的 mermaid 代码（含 ```mermaid 包裹）

    Returns:
        注入后的报告文本
    """
    insert_pos = heading_match.end()
    # 确保在标题行的换行符之后插入
    injection = f"\n\n{mermaid_block}\n\n"
    return report_text[:insert_pos] + injection + report_text[insert_pos:]


def _generate_competitor_mindmap(stats: Dict, personas: List[Dict]) -> str:
    """从竞品对比数据生成竞品定位思维导图 (mermaid mindmap)。

    从 stats["dimensional_stats"] 中提取含"竞品"/"品牌"/"对比"关键词的维度，
    构建 mermaid mindmap 格式的竞品定位图。

    Args:
        stats: 统计数据，含 dimensional_stats 子字典
        personas: 用户画像列表（未使用，保持接口一致）

    Returns:
        mermaid 代码块字符串（含 ```mermaid 包裹），数据不足时返回简化版
    """
    dimensional_stats = stats.get("dimensional_stats", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}

    # 提取竞品相关维度
    competitor_dims = {
        k: v for k, v in dimensional_stats.items()
        if any(kw in k for kw in ["竞品", "品牌", "对比"])
    }

    # 收集竞品数据（品牌名 + 提及次数）
    competitors = []
    for dim_key, dim_data in competitor_dims.items():
        valid_items = {
            val: count for val, count in dim_data.items()
            if val not in noise_values and count > 0
        }
        # 按提及次数降序排列，取前 5
        sorted_items = sorted(valid_items.items(), key=lambda x: x[1], reverse=True)[:5]
        for val, count in sorted_items:
            # 避免重复添加同一竞品
            if not any(c["name"] == val for c in competitors):
                competitors.append({"name": val, "count": count})

    # 按提及次数排序
    competitors.sort(key=lambda x: x["count"], reverse=True)
    competitors = competitors[:5]

    # 构建 mermaid mindmap
    lines = ["mindmap", "  root((竞品定位地图))"]

    if competitors:
        for comp in competitors:
            safe_name = _sanitize_mermaid_text(comp["name"])
            count_info = f"提及{comp['count']}次"
            lines.append(f"    [{safe_name}]")
            lines.append(f"      ({count_info})")
    else:
        # 数据不足时的简化版
        lines.append("    [无竞品数据]")
        lines.append("      (数据不足)")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"


def _generate_topic_mindmap(stats: Dict, personas: List[Dict]) -> str:
    """从标签统计数据生成话题聚类思维导图 (mermaid mindmap)。

    从 stats["top_tags"] 和 stats["dimensional_stats"] 中提取高频话题，
    按维度归类后构建 mermaid mindmap 格式的话题聚类图。

    Args:
        stats: 统计数据，含 top_tags 和 dimensional_stats
        personas: 用户画像列表（未使用，保持接口一致）

    Returns:
        mermaid 代码块字符串（含 ```mermaid 包裹），数据不足时返回简化版
    """
    top_tags = stats.get("top_tags", {})
    dimensional_stats = stats.get("dimensional_stats", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}

    # 按维度归类标签（维度 -> Top 3 值）
    dimension_topics = {}
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:
            continue
        dim_name, dim_value = tag_key.split(":", 1)
        if dim_value in noise_values:
            continue
        if dim_name not in dimension_topics:
            dimension_topics[dim_name] = []
        dimension_topics[dim_name].append({"value": dim_value, "count": count})

    # 每个维度取 Top 3
    for dim_name in dimension_topics:
        dimension_topics[dim_name].sort(key=lambda x: x["count"], reverse=True)
        dimension_topics[dim_name] = dimension_topics[dim_name][:3]

    # 取提及量最高的 5 个维度
    sorted_dims = sorted(
        dimension_topics.items(),
        key=lambda x: sum(item["count"] for item in x[1]),
        reverse=True,
    )[:5]

    # 构建 mermaid mindmap
    lines = ["mindmap", "  root((话题聚类))"]

    if sorted_dims:
        for dim_name, items in sorted_dims:
            # 维度名保留中文，去掉前缀下划线部分
            display_dim = dim_name.split("_")[-1] if "_" in dim_name else dim_name
            safe_dim = _sanitize_mermaid_text(display_dim)
            lines.append(f"    [{safe_dim}]")
            for item in items:
                safe_val = _sanitize_mermaid_text(item["value"])
                lines.append(f"      ({safe_val} {item['count']}次)")
    else:
        lines.append("    [无话题数据]")
        lines.append("      (数据不足)")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"



def _generate_action_matrix(stats: Dict, personas: List[Dict]) -> str:
    """从痛点/卖点数据生成行动优先级矩阵 (mermaid flowchart)。

    从情感分布和标签数据推断行动优先级，构建 mermaid flowchart 格式
    的行动仪表盘。

    Args:
        stats: 统计数据，含 sentiment 和 dimensional_stats
        personas: 用户画像列表

    Returns:
        mermaid 代码块字符串（含 ```mermaid 包裹），数据不足时返回简化版
    """
    dimensional_stats = stats.get("dimensional_stats", {})
    sentiment_data = stats.get("sentiment", {})
    top_tags = stats.get("top_tags", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}

    # 从负面标签中提取痛点（用于 Quick Win / Strategic Investment）
    pain_points = []
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:
            continue
        dim_name, dim_value = tag_key.split(":", 1)
        if dim_value in noise_values:
            continue
        # 识别可能的问题维度
        if any(kw in dim_name for kw in ["痛点", "不满", "问题", "缺点", "负面"]):
            pain_points.append({"value": dim_value, "count": count})

    pain_points.sort(key=lambda x: x["count"], reverse=True)

    # 从正面标签中提取优势
    selling_points = []
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:
            continue
        dim_name, dim_value = tag_key.split(":", 1)
        if dim_value in noise_values:
            continue
        if any(kw in dim_name for kw in ["卖点", "优势", "好评", "亮点", "正面"]):
            selling_points.append({"value": dim_value, "count": count})

    selling_points.sort(key=lambda x: x["count"], reverse=True)

    # 计算负面比例
    total = stats.get("total", 1)
    negative_count = sum(
        sentiment_data.get(s, 0)
        for s in ["不推荐", "强烈不推荐"]
    )
    negative_ratio = negative_count / total if total > 0 else 0

    # 构建行动建议
    quick_wins = []
    strategic = []
    low_priority = []

    # 高频痛点 -> Quick Win（容易改进且影响大）
    for pp in pain_points[:2]:
        safe_name = _sanitize_mermaid_text(pp["value"])
        quick_wins.append(f"{safe_name} - 影响{pp['count']}位用户")

    # 如果负面比例高，添加情感改进建议
    if negative_ratio > 0.2 and not quick_wins:
        pct = f"{negative_ratio * 100:.0f}%"
        quick_wins.append(f"改善负面评价 - {pct}差评率")

    # 中频痛点或优化项 -> Strategic Investment
    for pp in pain_points[2:4]:
        safe_name = _sanitize_mermaid_text(pp["value"])
        strategic.append(f"改进{safe_name} - 战略优化")

    # 优势相关 -> Strategic Investment（巩固优势）
    for sp in selling_points[:2]:
        safe_name = _sanitize_mermaid_text(sp["value"])
        strategic.append(f"巩固{safe_name} - {sp['count']}次正面提及")

    # Low Priority：如果数据不足则给默认建议
    if not low_priority:
        low_priority.append("监控长尾反馈趋势")

    # 兜底：如果所有行动列表都为空
    if not quick_wins and not strategic:
        quick_wins.append("分析热门评论反馈进行改进")
        strategic.append("制定差异化竞争策略")

    # 构建 mermaid flowchart
    lines = ["graph TD", "    A[行动仪表盘] --> B[快速见效]", "    A --> C[战略投入]", "    A --> D[低优先级]"]

    for i, qw in enumerate(quick_wins[:2], 1):
        lines.append(f"    B --> B{i}[{qw}]")

    for i, si in enumerate(strategic[:2], 1):
        lines.append(f"    C --> C{i}[{si}]")

    for i, lp in enumerate(low_priority[:1], 1):
        lines.append(f"    D --> D{i}[{lp}]")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"


def _generate_pain_points_matrix(stats: Dict, personas: List[Dict]) -> str:
    """从痛点/负面数据生成痛点严重性矩阵 (mermaid flowchart)。

    从标签数据中提取负面/痛点相关信息，按严重程度分级后构建
    mermaid flowchart 格式的痛点决策树。

    Args:
        stats: 统计数据，含 sentiment 和 dimensional_stats
        personas: 用户画像列表

    Returns:
        mermaid 代码块字符串（含 ```mermaid 包裹），数据不足时返回简化版
    """
    dimensional_stats = stats.get("dimensional_stats", {})
    sentiment_data = stats.get("sentiment", {})
    top_tags = stats.get("top_tags", {})
    noise_values = {"不明", "未提及", "无", "未知", "不明确", "其他"}

    # 提取负面/问题相关标签
    pain_items = []
    for tag_key, count in top_tags.items():
        if ":" not in tag_key:
            continue
        dim_name, dim_value = tag_key.split(":", 1)
        if dim_value in noise_values:
            continue
        if any(kw in dim_name for kw in ["痛点", "不满", "问题", "缺点", "负面", "抱怨"]):
            pain_items.append({"value": dim_value, "count": count, "dim": dim_name})

    pain_items.sort(key=lambda x: x["count"], reverse=True)

    total = stats.get("total", 1)
    severe_count = sum(
        sentiment_data.get(s, 0) for s in ["不推荐", "强烈不推荐"]
    )

    # 按严重程度分级
    critical = []
    severe = []
    moderate = []

    for item in pain_items:
        pct = item["count"] / total * 100 if total > 0 else 0
        entry = {
            "value": _sanitize_mermaid_text(item["value"]),
            "pct": f"{pct:.0f}%",
        }
        if pct >= 10:
            critical.append(entry)
        elif pct >= 5:
            severe.append(entry)
        else:
            moderate.append(entry)

    # 如果没有显式痛点数据，从负面情感比例推断
    if not pain_items and severe_count > 0:
        negative_pct = severe_count / total * 100
        critical.append({
            "value": "高差评率",
            "pct": f"{negative_pct:.0f}%",
        })

    # 构建 mermaid flowchart
    lines = [
        "graph TD",
        "    A[痛点分析] --> B[致命级]",
        "    A --> C[严重级]",
        "    A --> D[一般级]",
    ]

    for i, item in enumerate(critical[:2], 1):
        lines.append(f"    B --> B{i}[{item['value']} - {item['pct']}用户受影响]")

    for i, item in enumerate(severe[:2], 1):
        lines.append(f"    C --> C{i}[{item['value']} - {item['pct']}用户受影响]")

    for i, item in enumerate(moderate[:1], 1):
        lines.append(f"    D --> D{i}[{item['value']}]")

    # 如果某个级别为空，添加占位
    if not critical:
        lines.append("    B --> B1[暂无致命级问题]")
    if not severe:
        lines.append("    C --> C1[暂无严重级问题]")
    if not moderate:
        lines.append("    D --> D1[持续监控用户反馈]")

    mermaid_code = "\n".join(lines)
    return f"```mermaid\n{mermaid_code}\n```"


def _sanitize_mermaid_text(text: str) -> str:
    """清理文本使其适用于 mermaid 节点标签。

    mermaid 对特殊字符敏感（括号、引号等），但支持中文显示。
    此函数保留中文内容，仅移除 mermaid 语法中的保留字符，
    截断过长文本以避免节点溢出。

    语言规则：默认中文，英文专有名词和用户原话保持英文。

    Args:
        text: 原始文本（可能含中文、英文、特殊字符）

    Returns:
        清理后的安全文本字符串
    """
    if not text:
        return "N/A"

    # 移除 mermaid 语法中的保留字符（保留中文、英文、数字、空格、常用标点）
    cleaned = text.strip()
    for char in ['[', ']', '(', ')', '{', '}', '"', "'", '#', '&', '|', '%']:
        cleaned = cleaned.replace(char, '')

    # 压缩连续空格
    while '  ' in cleaned:
        cleaned = cleaned.replace('  ', ' ')

    cleaned = cleaned.strip()
    if not cleaned:
        return "N/A"

    # 截断到 40 字符，避免节点过长
    if len(cleaned) > 40:
        cleaned = cleaned[:37] + "..."

    return cleaned

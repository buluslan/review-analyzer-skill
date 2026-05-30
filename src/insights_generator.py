"""
洞察报告生成模块 V1.0 - CLI 原生版

统一使用 subprocess 调用宿主 CLI 引擎生成洞察报告。
支持 claude / opencode 双引擎，由 config 自动适配。
"""

import json
import logging
import subprocess
from typing import List, Dict
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
    
    # 将 Counter 转换为普通 dict (供 Gemini 使用全面数据)
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

"""
洞察报告生成模块 V1.0 - 双模洞察系统

重大变更：
- 支持双模式生成洞察报告：CLI 原生版 / Gemini API
- CLI 模式：使用 subprocess 调用宿主系统的 Claude Code CLI (claude -p)
- Gemini 模式：使用 Google Gemini API 生成高质量洞察报告
"""

import json
import logging
import subprocess
from typing import List, Dict
from collections import Counter
from datetime import datetime

# 尝试导入 Gemini，失败时标记为不可用
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from src.config import config, mask_api_key
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

    # 2. 统计高频标签
    # 格式: "维度_标签名:值" 如 "人群_性别:男性"
    tag_counter = Counter()
    exclude_values = {"未提及", "不明", "无"}

    for review in tagged_reviews:
        tags = review.get("tags", {})
        for tag_key, tag_value in tags.items():
            # 过滤掉无效值
            if tag_value and tag_value not in exclude_values:
                # 使用 "维度_标签名:值" 作为key
                combined_key = f"{tag_key}:{tag_value}"
                tag_counter[combined_key] += 1

    # 取 Top 30 标签
    top_tags = dict(tag_counter.most_common(30))

    # 2. 计算平均评分
    ratings = [r.get("rating", 0) for r in tagged_reviews if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    return {
        "total": total,
        "tagged": tagged_count,
        "sentiment": sentiment_dist,
        "top_tags": top_tags,
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

    根据 config.INSIGHTS_PROVIDER 选择 CLI 或 Gemini API

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
    # 获取格式化的提示词
    prompt = get_insights_prompt_txt(
        stats=stats,
        personas=personas,
        samples=golden_samples,
        asin=asin,
        product_name=product_name
    )

    # 根据配置选择生成方式
    if config.INSIGHTS_PROVIDER == "gemini":
        report_text = _generate_via_gemini(prompt, asin)
    else:  # 默认使用 CLI
        report_text = _generate_via_cli(prompt, asin)

    # V1.0 优化：剥离 <strategic_json> 标签，确保 Markdown 报告内容纯净
    if report_text and "<strategic_json>" in report_text:
        import re
        report_text = re.sub(r'<strategic_json>.*?</strategic_json>', '', report_text, flags=re.DOTALL).strip()

    return report_text


def _generate_via_gemini(
    prompt: str,
    asin: str
) -> str:
    """使用 Gemini API 生成洞察报告"""
    if not GEMINI_AVAILABLE:
        raise ImportError("google-generativeai 未安装，请运行: pip install google-generativeai")

    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 未配置")

    try:
        # 安全地记录API Key配置（仅显示后4位）
        logger.debug(f"配置 Gemini API Key: {mask_api_key(config.GEMINI_API_KEY)}")
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config=genai.types.GenerationConfig(
                temperature=config.GEMINI_TEMPERATURE,
                max_output_tokens=config.GEMINI_MAX_TOKENS,
            )
        )

        logger.debug(f"调用 Gemini API: ASIN={asin}")

        response = model.generate_content(prompt)
        report_text = response.text

        if not report_text:
            logger.error("Gemini API 返回空内容")
            return ""

        logger.info(f"成功生成洞察报告(Gemini): ASIN={asin}, 字数={len(report_text)}")
        return report_text

    except Exception as e:
        logger.error(f"Gemini API 调用失败: {str(e)}")
        return ""


def _generate_via_cli(prompt: str, asin: str) -> str:
    """使用 Claude Code CLI 生成洞察报告"""
    cmd = [config.CLAUDE_CLI_CMD, "-p", prompt]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=config.CLI_TIMEOUT,
        check=True
    )

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "未知错误"
        logger.error(f"Claude CLI 返回非零状态码: {error_msg}")
        return ""

    report_text = result.stdout.strip()
    if not report_text:
        logger.error("Claude CLI 返回空内容")
        return ""

    logger.info(f"成功生成洞察报告(CLI): ASIN={asin}, 字数={len(report_text)}")
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

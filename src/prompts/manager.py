"""
Prompt Manager Module V2.0

从独立的 .md 文件加载 prompt 模板，支持动态内容插入和条件章节控制。
将 Prompt 从 Python 代码中抽离为独立文件，便于迭代和维护。
"""

import ast
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ==================== 路径常量 ====================

PROMPTS_DIR = Path(__file__).parent
CHAPTERS_DIR = PROMPTS_DIR / "chapters"

# 所有可用的 prompt 模板文件
PROMPT_FILES: Dict[str, Path] = {
    "tagging": PROMPTS_DIR / "tagging.md",
    "persona": PROMPTS_DIR / "persona.md",
    "insights_v2": PROMPTS_DIR / "insights_v2.md",
}

# 章节配置：章节编号 -> 配置字典
CHAPTER_CONFIG: Dict[int, Dict[str, Any]] = {
    1: {"file": "chapter_01_overview.md", "conditional": False, "key": "overview"},
    2: {"file": "chapter_02_stats.md", "conditional": False, "key": "stats"},
    3: {"file": "chapter_03_persona.md", "conditional": False, "key": "persona"},
    4: {"file": "chapter_04_value.md", "conditional": False, "key": "value"},
    5: {"file": "chapter_05_painpoints.md", "conditional": False, "key": "painpoints"},
    6: {"file": "chapter_06_recommendations.md", "conditional": False, "key": "recommendations"},
    7: {"file": "chapter_07_opportunities.md", "conditional": False, "key": "opportunities"},
    8: {"file": "chapter_08_user_stories.md", "conditional": False, "key": "user_stories"},
    9: {
        "file": "chapter_09_time_trend.md",
        "conditional": True,
        "condition_field": "has_review_date",
        "key": "time_trend",
    },
    10: {"file": "chapter_10_sentiment_gap.md", "conditional": False, "key": "sentiment_gap"},
    11: {"file": "chapter_11_keyword_clustering.md", "conditional": False, "key": "keyword_clustering"},
    12: {"file": "chapter_12_purchase_funnel.md", "conditional": False, "key": "purchase_funnel"},
    13: {"file": "chapter_13_action_dashboard.md", "conditional": False, "key": "action_dashboard"},
}


class PromptLoadError(Exception):
    """Prompt 加载异常"""
    pass


# ==================== 核心加载函数 ====================


def load_prompt(name: str) -> str:
    """
    加载指定的 prompt 模板文件。

    Args:
        name: 模板名称，支持 'tagging', 'persona', 'insights_v2'

    Returns:
        模板文件内容字符串

    Raises:
        PromptLoadError: 文件不存在或读取失败
        ValueError: 未知的模板名称
    """
    if name not in PROMPT_FILES:
        available = ", ".join(PROMPT_FILES.keys())
        raise ValueError(f"未知的模板名称 '{name}'，可用模板: {available}")

    file_path = PROMPT_FILES[name]

    if not file_path.exists():
        raise PromptLoadError(f"模板文件不存在: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        logger.debug("成功加载模板: %s (%d 字符)", name, len(content))
        return content
    except OSError as e:
        raise PromptLoadError(f"读取模板文件失败 [{file_path}]: {e}") from e


def load_chapter(chapter_num: int) -> str:
    """
    加载指定章节的 prompt 模板。

    Args:
        chapter_num: 章节编号 (1-13)

    Returns:
        章节 prompt 内容字符串

    Raises:
        PromptLoadError: 章节文件不存在或读取失败
        ValueError: 章节编号不在 1-13 范围内
    """
    if chapter_num not in CHAPTER_CONFIG:
        raise ValueError(f"章节编号必须在 1-13 之间，当前: {chapter_num}")

    config = CHAPTER_CONFIG[chapter_num]
    file_path = CHAPTERS_DIR / config["file"]

    if not file_path.exists():
        raise PromptLoadError(f"章节文件不存在: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        logger.debug("成功加载章节 %d: %s (%d 字符)", chapter_num, config["file"], len(content))
        return content
    except OSError as e:
        raise PromptLoadError(f"读取章节文件失败 [{file_path}]: {e}") from e


def list_chapters() -> List[Dict[str, Any]]:
    """
    列出所有可用的章节配置信息。

    Returns:
        章节配置列表，每项包含 chapter_num, key, file, conditional 等字段
    """
    result: List[Dict[str, Any]] = []
    for num, config in CHAPTER_CONFIG.items():
        result.append({
            "chapter_num": num,
            "key": config["key"],
            "file": config["file"],
            "conditional": config["conditional"],
            "condition_field": config.get("condition_field"),
        })
    return result


def get_active_chapters(context: Optional[Dict[str, Any]] = None) -> List[int]:
    """
    获取当前条件下活跃的章节列表。

    Args:
        context: 条件上下文字典，用于判断条件章节是否启用

    Returns:
        活跃章节编号列表
    """
    return _resolve_conditionals(None, context)


def get_chapter_info(chapter_num: int) -> Optional[Dict[str, Any]]:
    """
    获取指定章节的配置信息。

    Args:
        chapter_num: 章节编号

    Returns:
        章节配置字典，不存在则返回 None
    """
    config = CHAPTER_CONFIG.get(chapter_num)
    if config is None:
        return None
    return {
        "chapter_num": chapter_num,
        "key": config["key"],
        "file": config["file"],
        "conditional": config["conditional"],
        "condition_field": config.get("condition_field"),
    }


# ==================== 内部工具函数 ====================


def _resolve_conditionals(
    chapters: Optional[List[int]],
    context: Optional[Dict[str, Any]],
) -> List[int]:
    """
    根据条件上下文解析最终需要包含的章节列表。

    Args:
        chapters: 指定的章节列表，None 表示包含所有适用章节
        context: 条件上下文字典，用于判断条件章节是否启用

    Returns:
        解析后的章节编号列表
    """
    if chapters is not None:
        target_chapters = chapters
    else:
        target_chapters = list(CHAPTER_CONFIG.keys())

    resolved: List[int] = []
    context = context or {}

    for num in target_chapters:
        if num not in CHAPTER_CONFIG:
            logger.warning("跳过无效章节编号: %d", num)
            continue

        config = CHAPTER_CONFIG[num]

        # 检查条件章节
        if config["conditional"]:
            condition_field = config.get("condition_field", "")
            if not context.get(condition_field, False):
                logger.info(
                    "跳过条件章节 %d（%s）：条件 '%s' 未满足",
                    num, config["key"], condition_field,
                )
                continue

        resolved.append(num)

    return resolved


def _render_template(template: str, variables: Dict[str, str]) -> str:
    """
    渲染模板，替换 {{PLACEHOLDER}} 格式的占位符。

    Args:
        template: 模板字符串
        variables: 变量字典，key 为占位符名称（大写），value 为替换内容

    Returns:
        渲染后的字符串
    """
    result = template

    for key, value in variables.items():
        placeholder = "{{" + key.upper() + "}}"
        result = result.replace(placeholder, str(value))

    # 检查未替换的占位符
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", result)
    if remaining:
        logger.warning("存在未替换的占位符: %s", remaining)

    return result


def _normalize_tags(tags: Any) -> dict:
    """将 tags 字段转换为 dict（处理字符串或异常情况）"""
    if isinstance(tags, dict):
        return tags
    if isinstance(tags, str):
        try:
            return ast.literal_eval(tags)
        except (ValueError, SyntaxError):
            return {}
    return {}


# ==================== 业务构建函数 ====================


def build_tagging_prompt(reviews: List[Dict[str, Any]]) -> str:
    """
    构建批量评论打标 prompt。

    Args:
        reviews: 评论列表，每条需包含 review_id, title, body, rating

    Returns:
        构建完成的 prompt 字符串

    Raises:
        PromptLoadError: 模板加载失败
        ValueError: 评论数据不完整
    """
    if not reviews:
        raise ValueError("评论列表不能为空")

    template = load_prompt("tagging")

    # 简化评论数据，只保留必要字段
    simplified_reviews: List[Dict[str, Any]] = []
    for r in reviews:
        if not r.get("review_id"):
            logger.warning("跳过缺少 review_id 的评论: %s", r.get("title", "unknown"))
            continue
        simplified_reviews.append({
            "review_id": r.get("review_id", ""),
            "title": r.get("title", ""),
            "body": r.get("body", ""),
            "rating": r.get("rating", ""),
        })

    if not simplified_reviews:
        raise ValueError("没有有效的评论数据（所有评论缺少 review_id）")

    reviews_json = json.dumps(simplified_reviews, ensure_ascii=False, indent=2)

    variables: Dict[str, str] = {
        "BATCH_SIZE": str(len(simplified_reviews)),
        "REVIEWS_DATA": reviews_json,
    }

    prompt = _render_template(template, variables)
    logger.info("构建打标 prompt 完成: %d 条评论, %d 字符", len(simplified_reviews), len(prompt))
    return prompt


def build_persona_prompt(
    tagged_data: List[Dict[str, Any]],
    total_reviews: int,
    tagged_reviews: int,
) -> str:
    """
    构建用户画像分析 prompt。

    Args:
        tagged_data: 打标后的评论数据列表
        total_reviews: 评论总量
        tagged_reviews: 有效打标数量

    Returns:
        构建完成的 prompt 字符串

    Raises:
        PromptLoadError: 模板加载失败
    """
    template = load_prompt("persona")

    tagged_json = json.dumps(tagged_data, ensure_ascii=False, indent=2)

    variables: Dict[str, str] = {
        "TOTAL_REVIEWS": str(total_reviews),
        "TAGGED_REVIEWS": str(tagged_reviews),
        "TAGGED_DATA": tagged_json,
    }

    prompt = _render_template(template, variables)
    logger.info("构建画像 prompt 完成: %d 条数据, %d 字符", len(tagged_data), len(prompt))
    return prompt


def build_insights_prompt(
    stats: Dict[str, Any],
    personas: List[Dict[str, Any]],
    samples: List[Dict[str, Any]],
    asin: str,
    product_name: Optional[str] = None,
    chapters: Optional[List[int]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    构建洞察报告 V2 prompt。

    Args:
        stats: 统计数据，需包含 total, tagged, sentiment, dimensional_stats, top_tags
        personas: 用户画像列表
        samples: 黄金样本列表
        asin: 产品 ASIN
        product_name: 产品名称（可选，默认使用 asin）
        chapters: 指定包含的章节列表（可选，None 表示包含所有适用章节）
        context: 条件上下文（可选），用于控制条件章节：
            - has_review_date (bool): 是否有评论日期数据，控制章节9
            - time_distribution_text (str): 时间分布数据文本

    Returns:
        构建完成的 prompt 字符串

    Raises:
        PromptLoadError: 模板或章节文件加载失败
    """
    template = load_prompt("insights_v2")

    # 解析条件章节
    context = context or {}
    resolved_chapters = _resolve_conditionals(chapters, context)

    # 构建章节 prompt 拼接
    chapter_prompts: List[str] = []
    for num in resolved_chapters:
        try:
            chapter_content = load_chapter(num)
            chapter_prompts.append(chapter_content)
        except PromptLoadError as e:
            logger.error("加载章节 %d 失败，跳过: %s", num, e)
    chapter_prompts_text = "\n\n---\n\n".join(chapter_prompts)

    # ---- 格式化用户画像 ----
    personas_details: List[str] = []
    for i, p in enumerate(personas):
        tags = _normalize_tags(p.get("tags", {}))
        detail = f"### 画像 {i + 1}: {p['name']} ({p['count']} 条)\n"
        detail += f"标签特征: {', '.join(f'{k}:{v}' for k, v in tags.items() if v)}"
        personas_details.append(detail)
    personas_details_text = "\n\n".join(personas_details) if personas_details else "无画像数据"

    # ---- 格式化情感分布 ----
    sentiment_data = stats.get("sentiment", {})
    total_count = max(stats.get("total", 1), 1)
    sentiment_dist = "\n".join(
        f"- **{s}**: {c} 条 ({c / total_count * 100:.1f}%)"
        for s, c in sentiment_data.items()
    ) if sentiment_data else "无情感分布数据"

    # ---- 格式化全维度标签分布（锁定数值表格） ----
    dimensional_stats = stats.get("dimensional_stats", {})
    if not dimensional_stats:
        dimensional_distribution = "无具体维度分布数据"
    else:
        dim_lines: List[str] = []
        for dim, count_dict in dimensional_stats.items():
            total_dim_count = max(sum(count_dict.values()), 1)
            table = f"| {dim} 类别 | 人数 | 占比 |\n| :--- | :--- | :--- |\n"
            for val, count in count_dict.items():
                table += f"| {val} | {count} | {count / total_dim_count * 100:.1f}% |\n"
            dim_lines.append(table)
        dimensional_distribution = "\n".join(dim_lines)

    # ---- 格式化高频标签 ----
    top_tags_data = stats.get("top_tags", {})
    top_tags = "\n".join(
        f"{i + 1}. **{t}**: {c} 次"
        for i, (t, c) in enumerate(list(top_tags_data.items())[:15])
    ) if top_tags_data else "无高频标签数据"

    # ---- 格式化黄金样本 ----
    samples_details: List[str] = []
    for i, s in enumerate(samples):
        tags = _normalize_tags(s.get("tags", {}))
        sample = f"### 样本 {i + 1}\n"
        sample += f"**情感**: {s.get('sentiment', '不明')}\n"
        sample += f"**内容**: {s.get('body', '')[:300]}...\n"
        sample += f"**标签**: {', '.join(f'{k}:{v}' for k, v in tags.items() if v)}"
        samples_details.append(sample)
    golden_samples = "\n\n".join(samples_details) if samples_details else "无样本数据"

    # ---- 时间分布数据 ----
    time_distribution = context.get("time_distribution_text", "无时间分布数据")

    # ---- 组装变量 ----
    variables: Dict[str, str] = {
        "TOTAL": str(stats.get("total", 0)),
        "TAGGED": str(stats.get("tagged", 0)),
        "ASIN": asin,
        "PRODUCT_NAME": product_name or asin,
        "PERSONAS_COUNT": str(len(personas)),
        "PERSONAS_DETAILS": personas_details_text,
        "SENTIMENT_DISTRIBUTION": sentiment_dist,
        "DIMENSIONAL_DISTRIBUTION": dimensional_distribution,
        "TOP_TAGS": top_tags,
        "SAMPLES_COUNT": str(len(samples)),
        "GOLDEN_SAMPLES": golden_samples,
        "TIME_DISTRIBUTION": time_distribution,
        "CHAPTER_PROMPTS": chapter_prompts_text,
    }

    prompt = _render_template(template, variables)

    active_chapters = [str(n) for n in resolved_chapters]
    logger.info(
        "构建洞察 V2 prompt 完成: 章节 [%s], %d 字符",
        ", ".join(active_chapters), len(prompt),
    )
    return prompt

"""
模板渲染引擎 V2.0 - 多模板 HTML 报告生成

从 src/templates/{template_name}/dashboard.html 加载模板，
将分析数据注入为 ``window.__ANALYSIS_DATA__ = {json}``，模板自行读取该全局变量渲染。

V2.1: 新增数据适配层，将原始分析数据转换为 JS 模板期望的扁平结构。
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from src.config import config

logger = logging.getLogger(__name__)

# 模板根目录
_TEMPLATES_ROOT = Path(__file__).parent / "templates"


# ---------------------------------------------------------------------------
# 模板发现
# ---------------------------------------------------------------------------

def _discover_templates() -> List[Dict[str, str]]:
    """扫描模板目录，返回所有可用模板。

    Returns:
        模板描述列表，每项包含 name / description / path。
    """
    results: List[Dict[str, str]] = []

    if not _TEMPLATES_ROOT.exists():
        logger.warning("模板根目录不存在: %s", _TEMPLATES_ROOT)
        return results

    for child in sorted(_TEMPLATES_ROOT.iterdir()):
        if not child.is_dir():
            continue
        dashboard_html = child / "dashboard.html"
        if not dashboard_html.exists():
            continue

        # 尝试读取 meta.json 获取描述，否则使用目录名
        meta_path = child / "meta.json"
        description = ""
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    description = meta.get("description", "")
            except Exception:
                pass

        if not description:
            description = f"{child.name} 模板"

        results.append({
            "name": child.name,
            "description": description,
            "path": str(dashboard_html),
        })

    return results


def list_templates() -> List[dict]:
    """返回当前可用的模板列表。

    Returns:
        ``[{"name": "premium-gold", "description": "..."}, ...]``
    """
    return _discover_templates()


# ---------------------------------------------------------------------------
# 数据适配层 — 将原始分析数据转换为 JS 模板期望的扁平结构
# ---------------------------------------------------------------------------

# 使用 Jinja2 {{ }} 语法的模板（不走 JS 数据注入）
_JINJA2_TEMPLATES = {"premium-gold"}

# ChartConfig.title 关键词 → 模板 JS charts_data key 的映射
_CHART_KEY_MAP = {
    "情感": "sentiment",
    "sentiment": "sentiment",
    "画像": "persona",
    "persona": "persona",
    "场景": "scenarios",
    "scenario": "scenarios",
    "使用场景": "scenarios",
    "满意度": "features",
    "satisfaction": "features",
    "功能": "features",
    "feature": "features",
    "价格": "price_perception",
    "price": "price_perception",
    "外观": "design_usability",
    "易用": "design_usability",
    "design": "design_usability",
    "usability": "design_usability",
    "耐用": "durability",
    "durability": "durability",
    "质量": "durability",
}

_FIELD_LABELS = [
    "严重性",
    "核心发现",
    "数据支撑",
    "用户原话",
    "根源分析",
    "归因分类",
    "影响范围",
    "瀑布效应",
    "行动建议",
    "画像",
    "核心诉求",
    "情感倾向",
    "使用体验",
    "关键原话",
    "用户如何描述好处",
    "期望落差",
]

_NOISE_VALUES = {"不明", "未提及", "无", "未知", "不明确", "其他", "无对比"}


def _match_chart_key(chart_title: str) -> str:
    """根据图表标题匹配模板 JS 期望的 charts_data key。"""
    title_lower = chart_title.lower()
    for keyword, key in _CHART_KEY_MAP.items():
        if keyword in title_lower:
            return key
    return ""


def _normalize_insights_markdown(insights_md: str) -> str:
    """Normalize generated markdown variants before extracting dashboard data."""
    if not insights_md:
        return ""

    text = re.sub(r"<whiteboard\b[^>]*></whiteboard>", "", insights_md)

    # Feishu export may collapse adjacent bold fields into one paragraph:
    # **严重性**：致命**核心发现**：...
    for label in _FIELD_LABELS:
        text = re.sub(rf"(?<!^)(\*\*{re.escape(label)}\*\*[：:])", r"\n\1", text)

    # Keep charts out of the fallback full-text section; the HTML dashboard
    # renders its own chart matrix from structured stats.
    text = re.sub(r"```mermaid\s+.*?```", "", text, flags=re.DOTALL)
    return text


def _extract_report_product_name(insights_md: str, fallback: str) -> str:
    """Infer a readable product name from the V2 report heading."""
    text = _normalize_insights_markdown(insights_md)
    match = re.search(r"^#\s+(.+?)(?:深度洞察分析报告|评论深度分析报告|深度分析报告)?\s*$", text, re.MULTILINE)
    if not match:
        return fallback

    name = match.group(1).strip()
    name = re.sub(r"\s*(评论)?深度.*$", "", name).strip()
    return name or fallback


def _plain_text(text: str) -> str:
    """Strip lightweight markdown markers for dashboard snippets."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text or "")
    text = re.sub(r"`(.+?)`", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_field(block: str, label: str) -> str:
    """Extract a bold-label field from a markdown block."""
    if not block:
        return ""

    next_labels = "|".join(re.escape(item) for item in _FIELD_LABELS if item != label)
    pattern = rf"\*\*{re.escape(label)}\*\*[：:]\s*(.+?)(?=\n\*\*(?:{next_labels})\*\*[：:]|\n-\s+\*\*|\n>\s*|\n###|\Z)"
    match = re.search(pattern, block, re.DOTALL)
    if not match:
        return ""

    value = match.group(1).strip()
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -")


def _extract_quotes(block: str) -> List[str]:
    """Extract quoted VOC snippets from markdown blockquotes and inline fields."""
    quotes = re.findall(r">\s*\"(.+?)\"", block)
    if not quotes:
        raw = _extract_field(block, "用户原话") or _extract_field(block, "关键原话")
        quotes = re.findall(r"\"(.+?)\"", raw) or ([raw] if raw else [])
    return [q.strip() for q in quotes if q.strip()][:3]


def _chart_to_js_config(chart: Any) -> Optional[dict]:
    """Convert ChartConfig to Chart.js config for premium-gold dashboard."""
    if not chart:
        return None

    try:
        from src.chart_engine import render_for_html
        return render_for_html(chart)
    except Exception:
        pass

    cc = chart.to_dict() if hasattr(chart, "to_dict") else chart
    if not isinstance(cc, dict):
        return None

    chart_type = cc.get("chart_type", "bar")
    if chart_type == "donut":
        chart_type = "doughnut"
    data = cc.get("data", {})
    values = data.get("values", data.get("data", []))
    labels = data.get("labels", [])
    colors = cc.get("config", {}).get("colors") or [
        "#d29922", "#79c0ff", "#7ee787", "#ff7b72", "#d2a8ff", "#ffa657"
    ]
    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [{
                "label": cc.get("title", ""),
                "data": values,
                "backgroundColor": colors[:len(values)],
            }],
        },
        "options": {"responsive": True, "maintainAspectRatio": False},
    }


def _dimension_bar_chart(title: str, dim_data: dict, horizontal: bool = False) -> Optional[dict]:
    """Build a compact Chart.js bar config from dimensional statistics."""
    if not dim_data:
        return None

    filtered = {
        k: v for k, v in dim_data.items()
        if k not in _NOISE_VALUES and isinstance(v, (int, float)) and v > 0
    }
    if not filtered:
        return None

    items = sorted(filtered.items(), key=lambda item: item[1], reverse=True)[:6]
    labels = [item[0] for item in items]
    values = [item[1] for item in items]
    colors = ["#d29922", "#79c0ff", "#7ee787", "#ff7b72", "#d2a8ff", "#ffa657"]
    options = {
        "responsive": True,
        "maintainAspectRatio": False,
        "plugins": {
            "title": {"display": True, "text": title, "color": "#f0f6fc", "font": {"size": 16}},
            "legend": {"display": False},
        },
        "scales": {
            "x": {"ticks": {"color": "#8b949e"}, "grid": {"color": "rgba(255,255,255,0.05)"}},
            "y": {"ticks": {"color": "#8b949e", "precision": 0}, "grid": {"color": "rgba(255,255,255,0.05)"}},
        },
    }
    if horizontal:
        options["indexAxis"] = "y"

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": title,
                "data": values,
                "backgroundColor": colors[:len(values)],
                "borderColor": "transparent",
                "borderWidth": 0,
            }],
        },
        "options": options,
    }


def _build_premium_dashboard(insights_sections: dict, summary: dict) -> dict:
    """Build the curated premium-gold dashboard schema.

    This layer deliberately translates the long report into board-ready
    narrative modules instead of mirroring markdown sections one by one.
    """
    overview = insights_sections.get("overview_insights", [])
    user_segments = insights_sections.get("user_segments", [])
    selling_points = insights_sections.get("selling_points", [])
    pain_points = insights_sections.get("pain_points", [])
    opportunities = insights_sections.get("opportunities", [])
    user_stories = insights_sections.get("user_stories", [])
    action_table = insights_sections.get("action_table", [])
    quick_wins = insights_sections.get("quick_wins", [])

    positive_rate = summary.get("positive_rate", 0)
    negative_rate = summary.get("negative_rate", 0)
    top_value = selling_points[0] if selling_points else {}
    top_risk = pain_points[0] if pain_points else {}
    top_action = action_table[0] if action_table else (quick_wins[0] if quick_wins else {})
    top_user = user_segments[0] if user_segments else {}

    risk_title = top_risk.get("title", "核心风险")
    value_title = top_value.get("title", "核心价值")
    if overview:
        hero_judgement = overview[0].get("title", "")
        hero_detail = overview[0].get("desc", "")
    else:
        hero_judgement = f"{positive_rate}% 正面信号已验证，但关键风险仍会限制口碑天花板"
        hero_detail = insights_sections.get("overview_lead", "")

    core_tension = (
        f"{positive_rate}% 正面评价证明产品价值成立，但 {negative_rate}% 负面评价集中指向"
        f"「{risk_title}」。当前看板的关键不是继续证明好评，而是识别哪一个短板会吞噬增长。"
    )

    # --- Quadrant 1: Audience — 从用户画像数据动态生成 ---
    if top_user:
        _audience_traits = "、".join(top_user.get("traits", [])[:3])
        _audience_need = top_user.get("need", "")
        _audience_parts = [p for p in [_audience_traits, _audience_need] if p]
        _audience_text = "核心人群特征：" + "；".join(_audience_parts) if _audience_parts else f"占比最高的用户群体为「{top_user.get('title', '核心用户')}」，需关注其核心诉求。"
    else:
        _audience_text = "数据不足以识别明确的核心人群画像，建议扩大样本量后重新分析。"

    # --- Quadrant 2: Value — 从卖点数据动态生成 ---
    if top_value:
        _value_finding = top_value.get("finding", "")
        _value_data = top_value.get("data", "")
        _value_parts = [p for p in [_value_finding, _value_data] if p]
        _value_text = "；".join(_value_parts) if _value_parts else f"核心价值点「{value_title}」已被正面评价验证。"
    else:
        _value_text = f"{positive_rate}% 正面评价已验证产品基本价值成立，但核心卖点提炼需要更多数据支撑。"

    # --- Quadrant 3: Risk — 从痛点数据动态生成 ---
    if top_risk:
        _risk_finding = top_risk.get("finding", "")
        _risk_severity = top_risk.get("severity", "")
        _risk_parts = [p for p in [f"严重性：{_risk_severity}" if _risk_severity and _risk_severity != "一般" else "", _risk_finding] if p]
        _risk_text = "；".join(_risk_parts) if _risk_parts else f"「{risk_title}」是当前最集中的负面反馈来源，需重点关注。"
    else:
        _risk_text = "当前数据未识别出显著风险点，建议持续监控负面评价趋势。"

    # --- Quadrant 4: Move — 从行动建议数据动态生成 ---
    if top_action:
        _move_action = top_action.get("action", top_action.get("title", ""))
        _move_impact = top_action.get("impact", top_action.get("desc", ""))
        _move_priority = top_action.get("priority", "")
        _move_prefix = f"[{_move_priority}] " if _move_priority else ""
        _move_parts = [p for p in [_move_action, _move_impact] if p]
        _move_text = _move_prefix + " → ".join(_move_parts) if _move_parts else "优先处理已识别的核心短板，再将已验证的优势转化为竞争力。"
    else:
        _move_text = "优先处理已识别的核心短板，再将已验证的优势转化为竞争力。"

    quadrants = [
        {"eyebrow": "Audience", "title": "核心人群", "text": _audience_text, "accent": "gold"},
        {"eyebrow": "Value", "title": "价值验证", "text": _value_text, "accent": "green"},
        {"eyebrow": "Risk", "title": "失控风险", "text": _risk_text, "accent": "red"},
        {"eyebrow": "Move", "title": "优先动作", "text": _move_text, "accent": "blue"},
    ]

    moat_cards = []
    for item in selling_points[:3]:
        moat_cards.append({
            "title": re.sub(r"^卖点\s*\d+[：:]\s*", "", item.get("title", "")),
            "text": item.get("finding", ""),
            "metric": item.get("data", ""),
            "quote": (item.get("quotes") or [""])[0],
        })

    vulnerability_cards = []
    for item in pain_points[:3]:
        vulnerability_cards.append({
            "title": re.sub(r"^痛点\s*#?\d+[：:]\s*", "", item.get("title", "")),
            "text": item.get("finding", ""),
            "metric": item.get("data", ""),
            "severity": item.get("severity", ""),
            "quote": (item.get("quotes") or [""])[0],
        })

    voc_cards = []
    for story in user_stories[:4]:
        quotes = story.get("quotes") or []
        voc_cards.append({
            "title": story.get("title", ""),
            "status": story.get("sentiment", "") or "Mixed Signal",
            "need": story.get("need", ""),
            "quote": quotes[0] if quotes else "",
            "analysis": story.get("profile", ""),
            "tone": story.get("sentiment_class", "mixed"),
        })

    if len(voc_cards) < 4:
        for segment in user_segments[: 4 - len(voc_cards)]:
            quotes = segment.get("quotes") or []
            voc_cards.append({
                "title": segment.get("title", ""),
                "status": segment.get("share", "") or "Segment",
                "need": segment.get("need", ""),
                "quote": quotes[0] if quotes else "",
                "analysis": "从评论语义中反推出的场景型人群，用于定位内容与 Listing 沟通重点。",
                "tone": "positive",
            })

    return {
        "hero_judgement": hero_judgement,
        "hero_detail": hero_detail,
        "core_tension": core_tension,
        "quadrants": quadrants,
        "moat_cards": moat_cards,
        "vulnerability_cards": vulnerability_cards,
        "voc_cards": voc_cards,
        "opportunity_cards": opportunities[:3],
    }


def _extract_charts_data_for_templates(
    chart_configs: list, statistics: dict
) -> dict:
    """从 ChartConfig 列表提取模板 JS 期望的 charts_data 结构。

    Returns:
        {"sentiment": {"labels": [...], "data": [...]}, ...}
    """
    charts_data: Dict[str, Any] = {}

    # 优先从 chart_configs 提取
    for cc in chart_configs:
        if hasattr(cc, "to_dict"):
            cc_dict = cc.to_dict()
        elif isinstance(cc, dict):
            cc_dict = cc
        else:
            continue

        title = cc_dict.get("title", "")
        key = _match_chart_key(title)
        if not key:
            continue

        data = cc_dict.get("data", {})
        labels = data.get("labels", [])
        values = data.get("values", data.get("data", []))

        if labels and values:
            charts_data[key] = {"labels": labels, "data": values}

    # 如果 chart_configs 没有覆盖所有 key，从 statistics 补充
    dimensional = statistics.get("dimensional_stats", {})
    fallback_dims = {
        "场景_使用场景": "scenarios",
        "功能_满意度": "features",
        "体验_价格感知": "price_perception",
        "体验_易用性": "design_usability",
        "质量_耐用性": "durability",
    }
    for dim_name, chart_key in fallback_dims.items():
        if chart_key in charts_data:
            continue
        dim_data = dimensional.get(dim_name, {})
        if not dim_data:
            continue
        # 过滤"不明/未提及"
        _noise = {"不明", "未提及", "无", "未知", "不明确", "其他"}
        filtered = {k: v for k, v in dim_data.items() if k not in _noise}
        if filtered:
            sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
            charts_data[chart_key] = {
                "labels": [k for k, v in sorted_items],
                "data": [v for k, v in sorted_items],
            }

    return charts_data


def _parse_strategic_json(insights_md: str) -> tuple:
    """从 insights_md 中提取 <strategic_json> 并解析为 strategy + execution_matrix。

    Returns:
        (strategy_dict, execution_matrix_list)
    """
    empty_strategy = {}
    empty_matrix = []

    if not insights_md:
        return empty_strategy, empty_matrix

    match = re.search(
        r"<strategic_json>\s*(\{.*?\})\s*</strategic_json>",
        insights_md,
        re.DOTALL,
    )
    if not match:
        return empty_strategy, empty_matrix

    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.warning("strategic_json 解析失败")
        return empty_strategy, empty_matrix

    # strategy: moat_pros / vulnerability_cons
    moat_pros = []
    for item in raw.get("moat", []):
        moat_pros.append({
            "title": item.get("title", ""),
            "desc": item.get("desc", ""),
        })

    vulnerability_cons = []
    for item in raw.get("vulnerability", []):
        vulnerability_cons.append({
            "title": item.get("title", ""),
            "desc": item.get("desc", ""),
        })

    strategy = {
        "moat_pros": moat_pros,
        "vulnerability_cons": vulnerability_cons,
    }

    # execution_matrix
    execution_matrix = raw.get("execution_matrix", [])

    return strategy, execution_matrix


def _build_voc_quotes(golden_samples: list, sentiment: dict) -> list:
    """从黄金样本提取 VOC 卡片数据。

    Returns:
        [{"profile": "用户名", "quote": "原话", "status": "正面/负面", "is_danger": bool}, ...]
    """
    voc = []
    positive_labels = {"强烈推荐", "推荐"}
    negative_labels = {"不推荐", "强烈不推荐"}

    for sample in golden_samples[:8]:
        body = sample.get("body", "")
        if not body or len(body) < 10:
            continue

        sent = sample.get("sentiment", "中立")
        is_danger = sent in negative_labels
        status = "Negative" if is_danger else ("Positive" if sent in positive_labels else "Neutral")

        # 用户画像简述
        tags = sample.get("tags", {})
        profile_parts = []
        for key in ["人群_性别", "人群_年龄段", "场景_使用场景"]:
            val = tags.get(key, "")
            if val and val not in ("不明", "未提及", "无"):
                profile_parts.append(val)
        profile = " · ".join(profile_parts) if profile_parts else "用户"

        # 截断过长引用
        quote = body[:200] + ("..." if len(body) > 200 else "")

        voc.append({
            "profile": profile,
            "quote": f'"{quote}"',
            "status": status,
            "is_danger": is_danger,
        })

    return voc


def _split_chapters(insights_md: str) -> list:
    """将 insights_md 按 ## 标题拆分为章节列表。

    Returns:
        [{"title": "章节标题", "content": "内容HTML"}, ...]
    """
    if not insights_md:
        return []

    chapters = []
    # 按 ## 分割（跳过 # 一级标题）
    parts = re.split(r"\n(?=## )", insights_md)

    for part in parts:
        lines = part.strip().split("\n")
        if not lines:
            continue

        first_line = lines[0].strip()
        if not first_line.startswith("## "):
            continue

        title = first_line[3:].strip()
        # 跳过 strategic_json 块和附录
        if title.startswith("Strategic") or title.startswith("附录"):
            continue

        content = "\n".join(lines[1:]).strip()
        if not content:
            continue

        # 简单 Markdown → HTML：段落、加粗、引用
        content_html = content
        # 引用块
        content_html = re.sub(
            r"^>\s*(.+)$",
            r"<blockquote>\1</blockquote>",
            content_html,
            flags=re.MULTILINE,
        )
        # 加粗
        content_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content_html)
        # 段落（双换行 → p 标签）
        paragraphs = content_html.split("\n\n")
        content_html = "".join(
            f"<p>{p.strip()}</p>" if p.strip() and not p.strip().startswith("<") else p
            for p in paragraphs
        )

        chapters.append({"title": title, "content": content_html})

    return chapters


def _transform_for_js_templates(
    analysis_data: dict, chart_configs: list
) -> dict:
    """将原始分析数据转换为 JS 模板期望的扁平结构。

    JS 模板期望的数据契约：
        {
            "meta": {"product_name": ..., "report_title": ..., "sample_size": ...},
            "kpis": [{"label": ..., "value": ..., "desc": ..., "is_danger": bool}],
            "charts_data": {"sentiment": {"labels": [...], "data": [...]}, ...},
            "strategy": {"moat_pros": [...], "vulnerability_cons": [...]},
            "execution_matrix": [...],
            "voc_quotes": [...],
            "market_insights": [...],
            "chapters": [{"title": ..., "content": ...}],
            "asin": "...",
            "total_reviews": 50,
            "avg_rating": 4.3,
            "title": "..."
        }
    """
    sentiment = analysis_data.get(
        "sentiment", analysis_data.get("sentiment_distribution", {})
    )
    statistics = analysis_data.get("statistics", {})
    summary = analysis_data.get("summary", {})
    golden_samples = analysis_data.get("golden_samples", [])
    insights_md = analysis_data.get("insights_md", "")

    total = summary.get("total", analysis_data.get("total_reviews", 0))
    avg_rating = summary.get("avg_rating", analysis_data.get("avg_rating", 0))
    asin = analysis_data.get("asin", "")

    # meta
    product_name = analysis_data.get("product_name", asin)
    meta = {
        "product_name": product_name,
        "report_title": f"{product_name} 评论深度分析",
        "sample_size": total,
    }

    # kpis
    positive_labels = {"强烈推荐", "推荐"}
    negative_labels = {"不推荐", "强烈不推荐"}
    positive = sum(sentiment.get(k, 0) for k in positive_labels)
    negative = sum(sentiment.get(k, 0) for k in negative_labels)
    kpis = [
        {"label": "总评论数", "value": str(total), "desc": "分析的评论总量"},
        {"label": "平均评分", "value": f"{avg_rating:.1f}", "desc": "满分 5.0"},
        {
            "label": "正面评价",
            "value": f"{positive / total * 100:.0f}%" if total else "N/A",
            "desc": f"{positive} 条正面评论",
        },
        {
            "label": "负面评价",
            "value": f"{negative / total * 100:.0f}%" if total else "N/A",
            "desc": f"{negative} 条负面评论",
            "is_danger": negative > positive,
        },
    ]

    # charts_data
    charts_data = _extract_charts_data_for_templates(chart_configs, statistics)

    # 如果 chart_configs 没有提供 sentiment 图表，从 sentiment dict 直接构建
    if "sentiment" not in charts_data and sentiment:
        labels = list(sentiment.keys())
        values = list(sentiment.values())
        charts_data["sentiment"] = {"labels": labels, "data": values}

    # strategy + execution_matrix
    # 优先从 insights_generator 的侧通道获取（generate_insights 剥离前缓存）
    strategy, execution_matrix = {}, []
    try:
        from src.insights_generator import get_last_strategic_data
        cached = get_last_strategic_data()
        if cached:
            moat_pros = [
                {"title": item.get("title", ""), "desc": item.get("desc", "")}
                for item in cached.get("moat", [])
            ]
            vuln_cons = [
                {"title": item.get("title", ""), "desc": item.get("desc", "")}
                for item in cached.get("vulnerability", [])
            ]
            strategy = {"moat_pros": moat_pros, "vulnerability_cons": vuln_cons}
            execution_matrix = cached.get("execution_matrix", [])
    except Exception:
        pass

    # 降级：尝试从 insights_md 中解析（如果未被剥离）
    if not strategy and insights_md:
        strategy, execution_matrix = _parse_strategic_json(insights_md)

    # voc_quotes
    voc_quotes = _build_voc_quotes(golden_samples, sentiment)

    # market_insights：复用 strategy 的 moat 数据
    market_insights = strategy.get("moat_pros", [])[:3]

    # chapters
    chapters = _split_chapters(insights_md)

    return {
        "meta": meta,
        "kpis": kpis,
        "charts_data": charts_data,
        "strategy": strategy,
        "execution_matrix": execution_matrix,
        "voc_quotes": voc_quotes,
        "market_insights": market_insights,
        "chapters": chapters,
        # 扁平字段供 header 读取
        "asin": asin,
        "total_reviews": total,
        "avg_rating": avg_rating,
        "title": meta["report_title"],
    }


# ---------------------------------------------------------------------------
# 数据注入
# ---------------------------------------------------------------------------

def _build_injection_script(
    analysis_data: dict, chart_configs: list, template_name: str = ""
) -> str:
    """构建数据注入脚本块。

    对于 JS 模板（非 premium-gold），使用 _transform_for_js_templates() 转换后的扁平结构。
    对于 premium-gold（Jinja2 模板），页面已在服务端完成渲染，仅注入最小元数据。
    """
    if template_name in _JINJA2_TEMPLATES:
        charts_serialized = []
        for cc in chart_configs:
            if hasattr(cc, "to_dict"):
                charts_serialized.append(cc.to_dict())
            elif isinstance(cc, dict):
                charts_serialized.append(cc)
        payload = {
            "meta": {
                "template": template_name,
                "asin": analysis_data.get("asin", ""),
                "analysis_date": analysis_data.get("analysis_date", ""),
            },
            "charts": charts_serialized,
        }
    else:
        # JS 模板：使用转换后的扁平结构
        payload = _transform_for_js_templates(analysis_data, chart_configs)

    json_str = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"<script>\nwindow.__ANALYSIS_DATA__ = {json_str};\n</script>"


def _inject_data_into_html(html_content: str, injection_script: str) -> str:
    """将注入脚本插入到 HTML 的 <head> 末尾或 <body> 开头。"""

    # 优先插入到 </head> 之前
    head_close = html_content.find("</head>")
    if head_close != -1:
        return html_content[:head_close] + injection_script + "\n" + html_content[head_close:]

    # 降级：插入到 <body> 之后
    body_open = html_content.find("<body")
    if body_open != -1:
        tag_end = html_content.find(">", body_open)
        if tag_end != -1:
            return html_content[: tag_end + 1] + "\n" + injection_script + "\n" + html_content[tag_end + 1 :]

    # 最终降级：直接拼接到开头
    return injection_script + "\n" + html_content


# ---------------------------------------------------------------------------
# Jinja2 变量替换（向后兼容现有模板）
# ---------------------------------------------------------------------------


def _md_to_html(text: str) -> str:
    """简单 Markdown → HTML 转换（用于 insights_md 片段）。

    优先使用 markdown 库，降级使用正则基础转换。
    """
    # 尝试 markdown 库
    try:
        import markdown as _md
        return _md.markdown(text, extensions=["tables", "fenced_code"])
    except ImportError:
        pass

    # 尝试 markdown-it-py
    try:
        from markdown_it import MarkdownIt
        md = MarkdownIt("commonmark", {"html": True}).enable("table")
        return md.render(text)
    except ImportError:
        pass

    # 降级：基础正则转换（保留纯文本，至少处理加粗和引用）
    html = text
    # 表格行 → 保持原样（CSS 可处理）
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"^>\s*(.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)
    html = re.sub(r"`{3}\w*\n.*?`{3}", "", html, flags=re.DOTALL)  # 移除代码块
    html = re.sub(r"`{3}.*?`{3}", "", html, flags=re.DOTALL)
    return html


def _split_insights_for_template(insights_md: str) -> dict:
    """将 V2.0 的 13 章 insights_md 拆分为模板可直接渲染的结构化数据。

    不做过度解析 — 只提取结构清晰的章节（Ch1/Ch4/Ch5/Ch6/Ch7/Ch8/Ch13），
    其余章节保留为 HTML 直接渲染。
    """
    if not insights_md:
        return {
            "overview_insights": [],
            "overview_lead": "",
            "strategy_direction": "",
            "overview_positioning": "",
            "user_segments": [],
            "selling_points": [],
            "pain_points": [],
            "improvements": {"product": [], "service": [], "expectation": []},
            "action_table": [],
            "quick_wins": [],
            "opportunities": [],
            "user_stories": [],
            "remaining_chapters_html": "",
        }

    insights_md = _normalize_insights_markdown(insights_md)

    # 按 ## 标题拆分
    parts = re.split(r"\n(?=## )", insights_md)
    chapters = {}
    for part in parts:
        lines = part.strip().split("\n")
        if not lines:
            continue
        title_line = lines[0].strip()
        if title_line.startswith("## "):
            title = title_line[3:].strip()
            content = "\n".join(lines[1:]).strip()
            chapters[title] = content

    # --- Ch1: 洞察总览 → 提取编号洞察列表 ---
    overview_insights = []
    overview_lead = ""
    strategy_direction = ""
    overview_positioning = ""
    for key, content in chapters.items():
        if "洞察总览" in key:
            lead_match = re.search(r"^(.+?)(?=\n\*\*核心洞察|\n\n\*\*核心洞察|\Z)", content, re.DOTALL)
            if lead_match:
                overview_lead = _plain_text(lead_match.group(1))

            # 提取编号列表 (1. **...** —— ...)
            insight_matches = re.findall(
                r"\d+\.\s+\*\*(.+?)\*\*\s*[—–-]+\s*(.+)", content
            )
            for title, desc in insight_matches:
                overview_insights.append({"title": title, "desc": desc})

            # 提取产品定位
            pos_match = re.search(r"\*\*产品定位[：:]*\*\*\s*(.+?)(?:\n\n|\n---|\Z)", content, re.DOTALL)
            if pos_match:
                overview_positioning = _plain_text(pos_match.group(1))

            strategy_match = re.search(r"\*\*战略方向[：:]*\*\*\s*(.+?)(?:\n\n|\n---|\Z)", content, re.DOTALL)
            if strategy_match:
                strategy_direction = _plain_text(strategy_match.group(1))
            break

    # --- Ch3: 用户画像 → 提取语义画像，替代低信度原始聚类 ---
    user_segments = []
    for key, content in chapters.items():
        if "用户画像" in key or "核心用户画像" in key:
            segment_parts = re.split(r"\n(?=### )", content)
            for segment in segment_parts:
                if not segment.strip().startswith("###"):
                    continue
                lines = segment.strip().split("\n")
                title = lines[0][4:].strip()
                body = "\n".join(lines[1:]).strip()

                need_match = re.search(r"\*\*核心诉求\*\*[：:]\s*(.+?)(?:\n|$)", body)
                share_match = re.search(r"\*\*样本占比\*\*[：:]\s*(.+?)(?:\n|$)", body)
                traits = re.findall(r"-\s+(.+)", body)
                traits = [
                    re.sub(r"\*\*(.+?)\*\*", r"\1", item).strip()
                    for item in traits
                    if "核心诉求" not in item and "样本占比" not in item and "典型原话" not in item
                ][:4]
                quotes = _extract_quotes(body)

                user_segments.append({
                    "title": re.sub(r"^画像\s*\d+[：:]\s*", "", title),
                    "need": need_match.group(1).strip() if need_match else "",
                    "share": share_match.group(1).strip() if share_match else "",
                    "traits": traits,
                    "quotes": quotes,
                })
            break

    # --- Ch4: 核心卖点 → 提取卖点卡片 ---
    selling_points = []
    for key, content in chapters.items():
        if "核心卖点" in key or "价值验证" in key:
            # 按 ### 卖点 N 拆分
            sp_parts = re.split(r"\n(?=### )", content)
            for sp in sp_parts:
                if not sp.strip().startswith("###"):
                    continue
                sp_lines = sp.strip().split("\n")
                sp_title = sp_lines[0][4:].strip()
                sp_body = "\n".join(sp_lines[1:]).strip()

                finding = _extract_field(sp_body, "核心发现")
                data = _extract_field(sp_body, "数据支撑")
                quotes = _extract_quotes(sp_body)

                selling_points.append({
                    "title": sp_title,
                    "finding": finding,
                    "data": data,
                    "quotes": quotes,
                })
            break

    # --- Ch5: 痛点 → 提取痛点卡片 ---
    pain_points = []
    for key, content in chapters.items():
        if "痛点" in key and "负面" in key:
            # 按 ### 痛点 #N 拆分
            pp_parts = re.split(r"\n(?=### )", content)
            for pp in pp_parts:
                if not pp.strip().startswith("###"):
                    continue
                pp_lines = pp.strip().split("\n")
                pp_title = pp_lines[0][4:].strip()
                pp_body = "\n".join(pp_lines[1:]).strip()

                severity = _extract_field(pp_body, "严重性") or "一般"
                finding = _extract_field(pp_body, "核心发现")
                data = _extract_field(pp_body, "数据支撑")
                quotes = _extract_quotes(pp_body)

                pain_points.append({
                    "title": pp_title,
                    "severity": severity,
                    "finding": finding,
                    "data": data,
                    "quotes": quotes,
                })
            break

    # --- Ch6: 改进建议 → 提取优先级行动项 ---
    improvements = {"product": [], "service": [], "expectation": []}
    for key, content in chapters.items():
        if "改进建议" in key:
            for category, label in [("product", "产品改进"), ("service", "服务优化"), ("expectation", "预期管理")]:
                section_match = re.search(
                    rf"###\s*{label}.*?\n(.+?)(?=\n###|\Z)", content, re.DOTALL
                )
                if section_match:
                    items_text = section_match.group(1)
                    # 提取 - [**P0**] **标题** — 描述
                    p_items = re.findall(
                        r"-\s*\[\*\*(P\d+)\*\*\]\s*\*\*(.+?)\*\*\s*[—–-]+\s*(.+?)(?:\n|$)",
                        items_text,
                    )
                    for priority, title, desc in p_items:
                        improvements[category].append({
                            "priority": priority,
                            "title": title,
                            "desc": desc.strip(),
                        })
            break

    # --- Ch7: 机会 → 提取机会卡片 ---
    opportunities = []
    for key, content in chapters.items():
        if "机会" in key or "差异化" in key:
            opp_parts = re.split(r"\n(?=### )", content)
            for opp in opp_parts:
                if not opp.strip().startswith("###"):
                    continue
                opp_lines = opp.strip().split("\n")
                opp_title = opp_lines[0][4:].strip()
                opp_body = "\n".join(opp_lines[1:]).strip()

                finding = _extract_field(opp_body, "核心发现")
                data = _extract_field(opp_body, "数据支撑")
                quotes = _extract_quotes(opp_body)

                opportunities.append({
                    "title": opp_title,
                    "finding": finding,
                    "data": data,
                    "quotes": quotes,
                })
            break

    # --- Ch8: 用户故事 → 提取故事卡片 ---
    user_stories = []
    for key, content in chapters.items():
        if "用户" in key and ("故事" in key or "解析" in key):
            story_parts = re.split(r"\n(?=### )", content)
            for story in story_parts:
                if not story.strip().startswith("###"):
                    continue
                s_lines = story.strip().split("\n")
                s_title = s_lines[0][4:].strip()
                s_body = "\n".join(s_lines[1:]).strip()

                profile = _extract_field(s_body, "画像")
                sentiment = _extract_field(s_body, "情感倾向")
                need = _extract_field(s_body, "核心诉求")
                quotes = _extract_quotes(s_body)

                # 情感分类（用于卡片颜色）
                is_positive = any(w in sentiment for w in ["正面", "积极"])
                is_negative = any(w in sentiment for w in ["负面", "消极"])
                sentiment_class = "positive" if is_positive else ("negative" if is_negative else "mixed")

                user_stories.append({
                    "title": s_title,
                    "profile": profile,
                    "sentiment": sentiment,
                    "sentiment_class": sentiment_class,
                    "need": need,
                    "quotes": quotes,
                })
            break

    # --- Ch13: 行动仪表盘 → 提取行动表格 + 快速胜利 ---
    action_table = []
    quick_wins = []
    for key, content in chapters.items():
        if "行动" in key and "仪表盘" in key:
            # 提取表格行
            table_rows = re.findall(
                r"\|\s*(.+?)\s*\|\s*(P\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
                content,
            )
            for row in table_rows:
                action_table.append({
                    "action": row[0].strip(),
                    "priority": row[1].strip(),
                    "impact": row[2].strip(),
                    "source": row[3].strip(),
                })

            # 提取快速胜利清单
            qw_section = re.search(r"###?\s*快速胜利.*?\n(.+?)(?=\n###|\Z)", content, re.DOTALL)
            if qw_section:
                qw_items = re.findall(r"\d+\.\s+\*\*(.+?)\*\*[：:]*\s*(.+?)(?=\n\d+\.|\Z)", qw_section.group(1), re.DOTALL)
                for qw_title, qw_desc in qw_items:
                    quick_wins.append({"title": qw_title, "desc": qw_desc.strip()})
            break

    # --- 剩余章节 → 直接渲染为 HTML ---
    remaining_keys = [
        k for k in chapters
        if not any(
            kw in k
            for kw in ["洞察总览", "核心卖点", "价值验证", "痛点", "负面归因",
                        "改进建议", "机会", "差异化", "用户", "故事", "解析", "行动", "仪表盘"]
        )
    ]
    remaining_parts = []
    for k in remaining_keys:
        remaining_parts.append(f"## {k}\n\n{chapters[k]}")
    remaining_md = "\n\n---\n\n".join(remaining_parts)

    # 将剩余章节 markdown → HTML
    remaining_html = _md_to_html(remaining_md) if remaining_md else ""

    return {
        "overview_insights": overview_insights,
        "overview_lead": overview_lead,
        "strategy_direction": strategy_direction,
        "overview_positioning": overview_positioning,
        "user_segments": user_segments,
        "selling_points": selling_points,
        "pain_points": pain_points,
        "improvements": improvements,
        "action_table": action_table,
        "quick_wins": quick_wins,
        "opportunities": opportunities,
        "user_stories": user_stories,
        "remaining_chapters_html": remaining_html,
    }


def _jinja2_render(
    template_content: str,
    analysis_data: dict,
    chart_configs: list,
) -> str:
    """使用 Jinja2 对模板中的 {{ }} 占位符进行渲染。"""
    if not JINJA2_AVAILABLE:
        raise RuntimeError("jinja2 未安装，无法渲染模板。请运行: pip install jinja2")

    # 准备模板上下文
    summary = analysis_data.get("summary", {})
    sentiment_distribution = analysis_data.get("sentiment", analysis_data.get("sentiment_distribution", {}))
    tag_statistics = analysis_data.get("tag_statistics", {})
    personas = analysis_data.get("personas", [])
    golden_samples = analysis_data.get("golden_samples", [])
    insights_md = analysis_data.get("insights_md", "")
    product_name = analysis_data.get("product_name", analysis_data.get("asin", ""))
    asin = analysis_data.get("asin", "")

    # 拆分 insights_md 为结构化章节
    insights_sections = _split_insights_for_template(insights_md)
    display_opportunities = [
        item for item in insights_sections["opportunities"]
        if item.get("finding") or item.get("data") or item.get("quotes")
    ]
    if (not product_name or product_name == asin) and insights_md:
        product_name = _extract_report_product_name(insights_md, product_name or asin)

    tagged_reviews = summary.get("tagged", summary.get("total", 0))
    positive_count = sum(sentiment_distribution.get(k, 0) for k in ("强烈推荐", "推荐"))
    negative_count = sum(sentiment_distribution.get(k, 0) for k in ("不推荐", "强烈不推荐"))
    positive_rate = round(positive_count / tagged_reviews * 100, 1) if tagged_reviews else 0
    negative_rate = round(negative_count / tagged_reviews * 100, 1) if tagged_reviews else 0
    summary_context = {
        "total_reviews": summary.get("total", 0),
        "tagged_reviews": tagged_reviews,
        "persona_count": len(insights_sections["user_segments"]) or len(personas),
        "avg_rating": summary.get("avg_rating", 0),
        "positive_rate": positive_rate,
        "negative_rate": negative_rate,
        "positive_count": positive_count,
        "negative_count": negative_count,
    }

    dashboard_charts = []
    supported_chart_types = {"bar", "pie", "donut", "line", "area", "radar"}
    for chart in chart_configs:
        cc = chart.to_dict() if hasattr(chart, "to_dict") else chart
        if not isinstance(cc, dict):
            continue
        if cc.get("chart_type") not in supported_chart_types:
            continue
        if "画像" in cc.get("title", ""):
            continue
        js_config = _chart_to_js_config(chart)
        if not js_config:
            continue
        idx = len(dashboard_charts)
        dashboard_charts.append({
            "id": f"dashboardChart{idx}",
            "title": cc.get("title", f"图表 {idx + 1}"),
            "type": cc.get("chart_type", ""),
            "config": js_config,
        })
        if len(dashboard_charts) >= 6:
            break

    dimensional_stats = analysis_data.get("dimensional_stats") or analysis_data.get("statistics", {}).get("dimensional_stats", {})
    fallback_chart_specs = [
        ("价格感知", "体验_价格感知", False),
        ("易用性体验", "体验_易用性", False),
        ("做工认知", "质量_做工", True),
        ("耐用性信号", "质量_耐用性", True),
    ]
    existing_titles = {item["title"] for item in dashboard_charts}
    for title, dim_key, horizontal in fallback_chart_specs:
        if len(dashboard_charts) >= 6:
            break
        if title in existing_titles:
            continue
        js_config = _dimension_bar_chart(title, dimensional_stats.get(dim_key, {}), horizontal)
        if not js_config:
            continue
        idx = len(dashboard_charts)
        dashboard_charts.append({
            "id": f"dashboardChart{idx}",
            "title": title,
            "type": "bar",
            "config": js_config,
        })

    context = {
        "asin": asin,
        "product_name": product_name,
        "analysis_date": analysis_data.get("analysis_date", ""),
        "summary": summary_context,
        "personas": personas,
        "sentiment_distribution": sentiment_distribution,
        "tag_statistics": tag_statistics,
        "golden_samples": golden_samples,
        "insights_md": insights_md,
        "dashboard_charts": dashboard_charts,
        "premium_dashboard": _build_premium_dashboard(insights_sections, summary_context),
        # V2.0 结构化章节
        "overview_insights": insights_sections["overview_insights"],
        "overview_lead": insights_sections["overview_lead"],
        "strategy_direction": insights_sections["strategy_direction"],
        "overview_positioning": insights_sections["overview_positioning"],
        "user_segments": insights_sections["user_segments"],
        "selling_points": insights_sections["selling_points"],
        "pain_points": insights_sections["pain_points"],
        "improvements": insights_sections["improvements"],
        "action_table": insights_sections["action_table"],
        "quick_wins": insights_sections["quick_wins"],
        "opportunities": display_opportunities,
        "user_stories": insights_sections["user_stories"],
        "remaining_chapters_html": insights_sections["remaining_chapters_html"],
    }

    template = jinja2.Template(template_content)
    return template.render(**context)


# ---------------------------------------------------------------------------
# 核心接口
# ---------------------------------------------------------------------------

def render(
    template_name: str,
    analysis_data: dict,
    chart_configs: list,
) -> str:
    """加载指定模板并渲染完整 HTML。

    工作流程：
      1. 定位 ``src/templates/{template_name}/dashboard.html``
      2. 先用 Jinja2 替换 ``{{ }}`` 占位符
      3. 将分析数据和图表配置注入为 ``window.__ANALYSIS_DATA__`` 全局变量

    Args:
        template_name: 模板目录名称，如 ``"premium-gold"``
        analysis_data: 分析结果字典
        chart_configs: ChartConfig 对象列表（来自 chart_engine）

    Returns:
        完整 HTML 字符串。

    Raises:
        FileNotFoundError: 模板文件不存在
        RuntimeError: jinja2 未安装
    """
    template_dir = _TEMPLATES_ROOT / template_name
    template_file = template_dir / "dashboard.html"

    if not template_file.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_file}")

    logger.info("加载模板: %s", template_file)

    # 1. 读取模板内容
    with open(template_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Jinja2 渲染
    html_content = _jinja2_render(html_content, analysis_data, chart_configs)

    # 3. 数据注入
    injection_script = _build_injection_script(analysis_data, chart_configs, template_name)
    html_content = _inject_data_into_html(html_content, injection_script)

    logger.info("模板渲染完成: %s (长度=%d)", template_name, len(html_content))
    return html_content

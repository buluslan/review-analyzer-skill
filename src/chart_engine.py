"""
图表引擎模块 V2.0 - 多目标图表生成

从分析结果 JSON 中提取数据，生成适用于不同输出目标的图表配置对象。
支持目标：HTML (Chart.js)、飞书 (lark-whiteboard DSL)。
图表类型：柱状图、饼图/环形图、折线图/面积图、雷达图、热力图、桑基图、词云。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ChartConfig:
    """单个图表的标准化配置对象。"""

    chart_type: str  # bar | pie | donut | line | area | radar | heatmap | sankey | wordcloud
    title: str
    data: Dict[str, Any]  # 至少包含 labels / values，复杂图表按类型扩展
    config: Dict[str, Any] = field(default_factory=dict)  # 颜色、选项等

    def to_dict(self) -> Dict[str, Any]:
        """序列化为普通字典。"""
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "data": self.data,
            "config": self.config,
        }


# ---------------------------------------------------------------------------
# 色彩方案 — premium-gold 风格
# ---------------------------------------------------------------------------

# 主色板：灵感来自 premium-gold 的深色 + 暖色调
PALETTE_PREMIUM_GOLD: List[str] = [
    "#d29922",  # accent-gold
    "#79c0ff",  # accent-blue
    "#7ee787",  # accent-teal
    "#ff7b72",  # accent-coral
    "#d2a8ff",  # accent-purple
    "#ffa657",  # orange
    "#f778ba",  # pink
    "#a5d6ff",  # light blue
]

# 情感色板
PALETTE_SENTIMENT: Dict[str, str] = {
    "强烈推荐": "#3fb950",
    "推荐": "#7ee787",
    "中立": "#8b949e",
    "不推荐": "#ff7b72",
    "强烈不推荐": "#da3633",
}

# 热力图色阶（从低到高）
HEATMAP_GRADIENT: List[str] = [
    "#161b22", "#1a3040", "#1f5060", "#2a7a5a",
    "#7ee787", "#d29922", "#ffa657", "#ff7b72",
]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _safe_get(d: Optional[Dict], key: str, default: Any = None) -> Any:
    """安全从字典取值。"""
    if not d:
        return default
    return d.get(key, default)


def _top_n(items: Dict[str, Any], n: int = 8) -> Dict[str, Any]:
    """按值降序截取前 n 项。"""
    if not items:
        return {}
    sorted_items = sorted(items.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
    return dict(sorted_items[:n])


def _extract_dimensional_data(
    tag_statistics: Optional[Dict[str, Dict[str, int]]],
    prefix: str,
    top_n: int = 8,
) -> Tuple[List[str], List[int]]:
    """从 dimensional_stats 中按前缀提取标签及计数。

    Returns:
        (labels, values)
    """
    if not tag_statistics:
        return [], []

    dim_data = _safe_get(tag_statistics, prefix, {})
    if not dim_data:
        return [], []

    top = _top_n(dim_data, top_n)
    labels = list(top.keys())
    values = list(top.values())
    return labels, values


# ---------------------------------------------------------------------------
# 图表生成器 — 各类型
# ---------------------------------------------------------------------------

def _build_sentiment_chart(sentiment: Optional[Dict[str, int]]) -> Optional[ChartConfig]:
    """情感分布 — 环形图。"""
    if not sentiment:
        return None

    ordered_keys = ["强烈推荐", "推荐", "中立", "不推荐", "强烈不推荐"]
    labels = [k for k in ordered_keys if k in sentiment and sentiment[k] > 0]
    values = [sentiment[k] for k in labels]
    colors = [PALETTE_SENTIMENT.get(k, "#8b949e") for k in labels]

    if not labels:
        return None

    return ChartConfig(
        chart_type="donut",
        title="情感分布",
        data={"labels": labels, "values": values},
        config={"colors": colors, "cutout": "60%"},
    )


def _build_persona_chart(personas: Optional[List[Dict]]) -> Optional[ChartConfig]:
    """用户画像分布 — 饼图。"""
    if not personas:
        return None

    labels = [p.get("name", f"画像{i+1}") for i, p in enumerate(personas)]
    values = [p.get("count", 0) for p in personas]
    colors = [PALETTE_PREMIUM_GOLD[i % len(PALETTE_PREMIUM_GOLD)] for i in range(len(labels))]

    if sum(values) == 0:
        return None

    return ChartConfig(
        chart_type="pie",
        title="用户画像分布",
        data={"labels": labels, "values": values},
        config={"colors": colors},
    )


def _build_scenario_chart(dimensional_stats: Optional[Dict]) -> Optional[ChartConfig]:
    """使用场景分布 — 柱状图。"""
    labels, values = _extract_dimensional_data(dimensional_stats, "场景_使用场景", top_n=8)
    if not labels:
        return None

    colors = [PALETTE_PREMIUM_GOLD[i % len(PALETTE_PREMIUM_GOLD)] for i in range(len(labels))]

    return ChartConfig(
        chart_type="bar",
        title="使用场景分布",
        data={"labels": labels, "values": values},
        config={"colors": colors, "xAxisLabel": "场景", "yAxisLabel": "评论数"},
    )


def _build_satisfaction_chart(dimensional_stats: Optional[Dict]) -> Optional[ChartConfig]:
    """功能满意度分布 — 水平柱状图。"""
    labels, values = _extract_dimensional_data(dimensional_stats, "功能_满意度", top_n=5)
    if not labels:
        return None

    # 按满意度从高到低排列
    order = ["超出预期", "非常满意", "满意", "符合预期", "一般", "不满意", "低于预期", "非常不满意"]
    label_value_map = dict(zip(labels, values))
    labels = [o for o in order if o in label_value_map]
    values = [label_value_map[l] for l in labels]

    if not labels:
        return None

    colors = [PALETTE_PREMIUM_GOLD[i % len(PALETTE_PREMIUM_GOLD)] for i in range(len(labels))]

    return ChartConfig(
        chart_type="bar",
        title="功能满意度分布",
        data={"labels": labels, "values": values},
        config={"colors": colors, "horizontal": True, "xAxisLabel": "评论数", "yAxisLabel": "满意度"},
    )


def _build_dimension_radar(tag_statistics: Optional[Dict]) -> Optional[ChartConfig]:
    """多维度综合雷达图。"""
    if not tag_statistics:
        return None

    # 收集各维度正评率
    dimensions: Dict[str, float] = {}
    positive_keywords = {
        "功能_满意度": ["超出预期", "非常满意", "满意", "符合预期"],
        "质量_材质": ["优秀", "良好", "优质"],
        "质量_做工": ["精细", "良好"],
        "质量_耐用性": ["耐用", "长久"],
        "体验_舒适度": ["舒适", "很舒适"],
        "体验_易用性": ["简单", "容易"],
        "体验_外观设计": ["满意", "喜欢", "很喜欢"],
    }

    for dim_key, positive_vals in positive_keywords.items():
        dim_data = _safe_get(tag_statistics, dim_key, {})
        total = sum(dim_data.values()) if dim_data else 0
        if total == 0:
            continue
        positive_count = sum(dim_data.get(v, 0) for v in positive_vals)
        rate = round(positive_count / total * 100, 1)
        # 用短名称
        short_name = dim_key.split("_", 1)[-1] if "_" in dim_key else dim_key
        dimensions[short_name] = rate

    if len(dimensions) < 3:
        return None

    labels = list(dimensions.keys())
    values = list(dimensions.values())

    return ChartConfig(
        chart_type="radar",
        title="多维度满意度雷达图",
        data={"labels": labels, "values": values, "datasets": [{"label": "正评率 (%)", "values": values}]},
        config={"color": PALETTE_PREMIUM_GOLD[0], "maxValue": 100},
    )


def _build_heatmap_chart(dimensional_stats: Optional[Dict]) -> Optional[ChartConfig]:
    """功能满意度交叉热力图。"""
    if not dimensional_stats:
        return None

    satisfaction = _safe_get(dimensional_stats, "功能_满意度", {})
    features_raw = _safe_get(dimensional_stats, "功能_具体功能", {})

    if not satisfaction or not features_raw:
        return None

    # 取前 6 个满意度类别
    sat_labels = list(_top_n(satisfaction, 5).keys())
    # 取前 8 个功能关键词
    feat_labels = list(_top_n(features_raw, 8).keys())

    if not sat_labels or not feat_labels:
        return None

    # 生成模拟矩阵数据（真实场景需要交叉统计）
    # 这里用各值的占比作为热力值
    sat_total = sum(satisfaction.values()) or 1
    matrix: List[List[float]] = []
    for _ in feat_labels:
        row = [round(satisfaction.get(s, 0) / sat_total * 100, 1) for s in sat_labels]
        matrix.append(row)

    return ChartConfig(
        chart_type="heatmap",
        title="功能 x 满意度 热力图",
        data={
            "xLabels": sat_labels,
            "yLabels": feat_labels,
            "matrix": matrix,
        },
        config={"gradient": HEATMAP_GRADIENT, "unit": "%"},
    )


def _build_price_sentiment_sankey(
    dimensional_stats: Optional[Dict],
    sentiment: Optional[Dict],
) -> Optional[ChartConfig]:
    """价格感知 → 情感流向桑基图。"""
    if not dimensional_stats or not sentiment:
        return None

    price_data = _safe_get(dimensional_stats, "体验_价格感知", {})
    if not price_data:
        return None

    price_labels = list(_top_n(price_data, 5).keys())
    sentiment_labels = [k for k in ["强烈推荐", "推荐", "中立", "不推荐", "强烈不推荐"] if k in sentiment]

    if not price_labels or not sentiment_labels:
        return None

    # 构建简化的桑基连接
    links: List[Dict[str, Any]] = []
    for i, p_label in enumerate(price_labels):
        for j, s_label in enumerate(sentiment_labels):
            # 简化：按索引权重分配，实际需要交叉统计
            weight = price_data.get(p_label, 0) * sentiment.get(s_label, 1) // max(sum(sentiment.values()), 1)
            if weight > 0:
                links.append({
                    "source": p_label,
                    "target": s_label,
                    "value": max(weight, 1),
                })

    if not links:
        return None

    return ChartConfig(
        chart_type="sankey",
        title="价格感知 → 情感流向",
        data={
            "nodes": list(set(
                [l["source"] for l in links] + [l["target"] for l in links]
            )),
            "links": links,
        },
        config={
            "nodeColors": PALETTE_PREMIUM_GOLD[:5] + list(PALETTE_SENTIMENT.values())[:5],
        },
    )


def _build_wordcloud_chart(top_tags: Optional[Dict[str, int]]) -> Optional[ChartConfig]:
    """高频标签词云。"""
    if not top_tags:
        return None

    words = _top_n(top_tags, 30)
    if not words:
        return None

    # 构建词云数据格式
    word_list = [{"text": k, "weight": v} for k, v in words.items()]

    return ChartConfig(
        chart_type="wordcloud",
        title="高频标签词云",
        data={"words": word_list},
        config={
            "colors": PALETTE_PREMIUM_GOLD,
            "minWeight": 1,
        },
    )


# ---------------------------------------------------------------------------
# 核心接口
# ---------------------------------------------------------------------------

def generate_all_charts(analysis_data: dict) -> List[ChartConfig]:
    """根据分析结果字典，生成全部图表配置列表。

    Args:
        analysis_data: 分析结果 JSON，至少包含以下顶层键：
            - sentiment (dict): 情感分布
            - personas (list): 用户画像
            - dimensional_stats (dict): 维度统计
            - tag_statistics (dict): 标签统计
            - top_tags (dict): 高频标签

    Returns:
        所有成功构建的 ChartConfig 列表（空数据图表自动跳过）。
    """
    sentiment = analysis_data.get("sentiment", analysis_data.get("sentiment_distribution"))
    personas = analysis_data.get("personas", [])
    statistics = analysis_data.get("statistics", {})
    dimensional_stats = (
        analysis_data.get("dimensional_stats")
        or statistics.get("dimensional_stats")
        or analysis_data.get("tag_statistics", {})
    )
    tag_statistics = (
        analysis_data.get("tag_statistics")
        or statistics.get("dimensional_stats")
        or analysis_data.get("dimensional_stats", {})
    )
    top_tags = analysis_data.get("top_tags", {})

    builders = [
        lambda: _build_sentiment_chart(sentiment),
        lambda: _build_persona_chart(personas),
        lambda: _build_scenario_chart(dimensional_stats),
        lambda: _build_satisfaction_chart(dimensional_stats),
        lambda: _build_dimension_radar(tag_statistics),
        lambda: _build_heatmap_chart(dimensional_stats),
        lambda: _build_price_sentiment_sankey(dimensional_stats, sentiment),
        lambda: _build_wordcloud_chart(top_tags),
    ]

    charts: List[ChartConfig] = []
    for builder in builders:
        try:
            chart = builder()
            if chart is not None:
                charts.append(chart)
        except Exception as exc:
            logger.warning("图表构建异常，已跳过: %s", exc)

    logger.info("共生成 %d 个图表配置", len(charts))
    return charts


# ---------------------------------------------------------------------------
# 渲染器 — HTML (Chart.js)
# ---------------------------------------------------------------------------

def render_for_html(chart: ChartConfig) -> dict:
    """将 ChartConfig 转换为 Chart.js 兼容的配置字典。

    Returns:
        可直接传给 ``new Chart(ctx, config)`` 的 JSON 对象。
    """
    chart_type = chart.chart_type
    colors = chart.config.get("colors", PALETTE_PREMIUM_GOLD)

    base: Dict[str, Any] = {
        "type": chart_type,
        "options": {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": chart.title, "color": "#f0f6fc", "font": {"size": 16}},
                "legend": {"labels": {"color": "#8b949e"}},
            },
        },
    }

    if chart_type in ("bar",):
        base["type"] = "bar"
        base["data"] = {
            "labels": chart.data.get("labels", []),
            "datasets": [{
                "label": chart.title,
                "data": chart.data.get("values", []),
                "backgroundColor": colors[:len(chart.data.get("values", []))],
                "borderColor": "transparent",
                "borderWidth": 0,
            }],
        }
        if chart.config.get("horizontal"):
            base["options"]["indexAxis"] = "y"

    elif chart_type in ("pie", "donut"):
        base["type"] = "doughnut" if chart_type == "donut" else "pie"
        cutout = chart.config.get("cutout", "0%") if chart_type == "donut" else "0%"
        base["data"] = {
            "labels": chart.data.get("labels", []),
            "datasets": [{
                "data": chart.data.get("values", []),
                "backgroundColor": colors[:len(chart.data.get("values", []))],
                "borderColor": "#161b22",
                "borderWidth": 2,
            }],
        }
        base["options"]["cutout"] = cutout

    elif chart_type in ("line", "area"):
        base["type"] = "line"
        fill = chart_type == "area"
        base["data"] = {
            "labels": chart.data.get("labels", []),
            "datasets": [{
                "label": chart.title,
                "data": chart.data.get("values", []),
                "borderColor": colors[0] if colors else "#d29922",
                "backgroundColor": (colors[0] + "33") if colors else "#d2992233",
                "fill": fill,
                "tension": 0.4,
                "pointBackgroundColor": colors[0] if colors else "#d29922",
            }],
        }

    elif chart_type == "radar":
        base["type"] = "radar"
        datasets = chart.data.get("datasets", [])
        chart_datasets = []
        for idx, ds in enumerate(datasets):
            c = colors[idx % len(colors)] if colors else "#d29922"
            chart_datasets.append({
                "label": ds.get("label", chart.title),
                "data": ds.get("values", []),
                "borderColor": c,
                "backgroundColor": c + "33",
                "pointBackgroundColor": c,
            })
        base["data"] = {"labels": chart.data.get("labels", []), "datasets": chart_datasets}
        base["options"]["scales"] = {
            "r": {
                "angleLines": {"color": "#30363d"},
                "grid": {"color": "#30363d"},
                "pointLabels": {"color": "#8b949e"},
                "ticks": {"color": "#8b949e", "backdropColor": "transparent"},
                "max": chart.config.get("maxValue", 100),
            }
        }

    elif chart_type == "heatmap":
        # Chart.js 原生不支持热力图，使用 chartjs-chart-matrix 插件格式
        x_labels = chart.data.get("xLabels", [])
        y_labels = chart.data.get("yLabels", [])
        matrix = chart.data.get("matrix", [])
        gradient = chart.config.get("gradient", HEATMAP_GRADIENT)

        flat_data = []
        for yi, row in enumerate(matrix):
            for xi, val in enumerate(row):
                flat_data.append({"x": xi, "y": yi, "v": val})

        base["type"] = "matrix"
        base["data"] = {
            "datasets": [{
                "label": chart.title,
                "data": flat_data,
                "backgroundColor": gradient[0],
                "width": {"gt": 1},
                "height": {"gt": 1},
            }],
        }
        base["options"]["scales"] = {
            "x": {
                "type": "category",
                "labels": x_labels,
                "ticks": {"color": "#8b949e"},
                "grid": {"color": "#30363d"},
            },
            "y": {
                "type": "category",
                "labels": y_labels,
                "ticks": {"color": "#8b949e"},
                "grid": {"color": "#30363d"},
            },
        }

    elif chart_type == "sankey":
        # Chart.js 桑基图需要 chartjs-chart-sankey 插件
        base["type"] = "sankey"
        nodes = chart.data.get("nodes", [])
        links = chart.data.get("links", [])
        node_colors = chart.config.get("nodeColors", PALETTE_PREMIUM_GOLD)

        color_map = {n: node_colors[i % len(node_colors)] for i, n in enumerate(nodes)}
        base["data"] = {
            "datasets": [{
                "label": chart.title,
                "data": links,
                "colorFrom": lambda ctx: color_map.get(ctx.dataset.data[ctx.dataIndex]["source"], "#d29922"),
                "colorTo": lambda ctx: color_map.get(ctx.dataset.data[ctx.dataIndex]["target"], "#d29922"),
                "color": "transparent",
                "borderWidth": 0,
            }],
        }
        base["options"]["plugins"]["tooltip"] = {
            "callbacks": {
                "title": lambda ctx: "",
                "label": lambda ctx: (
                    f"{ctx.dataset.data[ctx.dataIndex]['source']} → "
                    f"{ctx.dataset.data[ctx.dataIndex]['target']}: "
                    f"{ctx.dataset.data[ctx.dataIndex]['value']}"
                ),
            }
        }

    elif chart_type == "wordcloud":
        # Chart.js 词云需要 chartjs-chart-wordcloud 插件
        words = chart.data.get("words", [])
        wc_colors = chart.config.get("colors", PALETTE_PREMIUM_GOLD)
        min_w = chart.config.get("minWeight", 1)

        base["type"] = "wordCloud"
        base["data"] = {
            "labels": [w["text"] for w in words],
            "datasets": [{
                "label": chart.title,
                "data": [max(w["weight"], min_w) for w in words],
                "color": wc_colors,
            }],
        }
        base["options"]["plugins"]["legend"] = {"display": False}

    else:
        logger.warning("未知的 chart_type: %s，返回基础配置", chart_type)

    return base


# ---------------------------------------------------------------------------
# 渲染器 — 飞书 (lark-whiteboard DSL)
# ---------------------------------------------------------------------------

def render_for_feishu(chart: ChartConfig) -> dict:
    """将 ChartConfig 转换为 lark-whiteboard DSL 格式。

    飞书白板 DSL 使用简化的 JSON 描述，包含 type、title、elements 等字段。
    由于 lark-whiteboard 并非标准图表库，此处生成的是一种中间 DSL，
    由 ``feishu_sync`` 在调用白板 API 时进一步映射。

    Returns:
        符合 lark-whiteboard 预期的 DSL 字典。
    """
    chart_type = chart.chart_type
    colors = chart.config.get("colors", PALETTE_PREMIUM_GOLD)

    dsl: Dict[str, Any] = {
        "type": chart_type,
        "title": chart.title,
        "style": {
            "background": "#161b22",
            "titleColor": "#f0f6fc",
            "textColor": "#8b949e",
            "accentColor": colors[0] if colors else "#d29922",
        },
    }

    if chart_type in ("bar",):
        dsl["elements"] = [
            {"label": label, "value": value, "color": colors[i % len(colors)]}
            for i, (label, value) in enumerate(zip(
                chart.data.get("labels", []),
                chart.data.get("values", []),
            ))
        ]

    elif chart_type in ("pie", "donut"):
        dsl["elements"] = [
            {"label": label, "value": value, "color": colors[i % len(colors)]}
            for i, (label, value) in enumerate(zip(
                chart.data.get("labels", []),
                chart.data.get("values", []),
            ))
        ]
        if chart_type == "donut":
            dsl["style"]["cutout"] = chart.config.get("cutout", "60%")

    elif chart_type in ("line", "area"):
        dsl["points"] = [
            {"x": label, "y": value}
            for label, value in zip(
                chart.data.get("labels", []),
                chart.data.get("values", []),
            )
        ]
        dsl["fill"] = chart_type == "area"

    elif chart_type == "radar":
        dsl["axes"] = chart.data.get("labels", [])
        dsl["series"] = [
            {"name": ds.get("label", ""), "values": ds.get("values", [])}
            for ds in chart.data.get("datasets", [])
        ]

    elif chart_type == "heatmap":
        dsl["xLabels"] = chart.data.get("xLabels", [])
        dsl["yLabels"] = chart.data.get("yLabels", [])
        dsl["cells"] = chart.data.get("matrix", [])
        dsl["style"]["gradient"] = chart.config.get("gradient", HEATMAP_GRADIENT)

    elif chart_type == "sankey":
        dsl["nodes"] = chart.data.get("nodes", [])
        dsl["links"] = chart.data.get("links", [])
        dsl["style"]["nodeColors"] = chart.config.get("nodeColors", PALETTE_PREMIUM_GOLD)

    elif chart_type == "wordcloud":
        dsl["words"] = chart.data.get("words", [])
        dsl["style"]["colors"] = colors

    else:
        logger.warning("未知的 chart_type 用于飞书 DSL: %s", chart_type)
        dsl["raw"] = chart.data

    return dsl

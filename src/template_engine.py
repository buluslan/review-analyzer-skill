"""
模板渲染引擎 V2.0 - 多模板 HTML 报告生成

从 src/templates/{template_name}/dashboard.html 加载模板，
将分析数据注入为 ``window.__ANALYSIS_DATA__ = {json}``，模板自行读取该全局变量渲染。
"""

import json
import logging
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
# 数据注入
# ---------------------------------------------------------------------------

def _build_injection_script(analysis_data: dict, chart_configs: list) -> str:
    """构建数据注入脚本块。

    生成 ``<script>window.__ANALYSIS_DATA__ = {...}; window.__CHART_CONFIGS__ = [...];</script>``
    """
    # 将 ChartConfig 对象序列化
    charts_serialized = []
    for cc in chart_configs:
        if hasattr(cc, "to_dict"):
            charts_serialized.append(cc.to_dict())
        elif isinstance(cc, dict):
            charts_serialized.append(cc)
        else:
            charts_serialized.append(str(cc))

    payload = {
        "analysis": analysis_data,
        "charts": charts_serialized,
    }

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

def _jinja2_render(
    template_content: str,
    analysis_data: dict,
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

    context = {
        "asin": asin,
        "product_name": product_name,
        "analysis_date": analysis_data.get("analysis_date", ""),
        "summary": {
            "total_reviews": summary.get("total", 0),
            "tagged_reviews": summary.get("tagged", summary.get("total", 0)),
            "persona_count": len(personas),
            "avg_rating": summary.get("avg_rating", 0),
        },
        "personas": personas,
        "sentiment_distribution": sentiment_distribution,
        "tag_statistics": tag_statistics,
        "golden_samples": golden_samples,
        "insights_md": insights_md,
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
    html_content = _jinja2_render(html_content, analysis_data)

    # 3. 数据注入
    injection_script = _build_injection_script(analysis_data, chart_configs)
    html_content = _inject_data_into_html(html_content, injection_script)

    logger.info("模板渲染完成: %s (长度=%d)", template_name, len(html_content))
    return html_content

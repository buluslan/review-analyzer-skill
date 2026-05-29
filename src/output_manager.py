"""
输出管理器 V2.0

统一管理所有输出通道：
- MD 洞察报告（始终生成）
- HTML 可视化看板（始终生成，用户选择模板）
- 飞书同步（可选：文档 + 画板图表）
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import config
from src.chart_engine import ChartConfig, generate_all_charts
from src.template_engine import list_templates, render

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Markdown 报告生成
# ---------------------------------------------------------------------------

def _build_md_content(analysis_data: dict, creator: str, asin: str) -> str:
    """构建 Markdown 报告正文。

    Args:
        analysis_data: 分析结果字典
        creator: 报告署名
        asin: 产品 ASIN

    Returns:
        Markdown 字符串。
    """
    from datetime import datetime

    product_name = analysis_data.get("product_name", asin)
    summary = analysis_data.get("summary", {})
    sentiment = analysis_data.get("sentiment", analysis_data.get("sentiment_distribution", {}))
    top_tags = analysis_data.get("top_tags", {})
    personas = analysis_data.get("personas", [])
    insights_md = analysis_data.get("insights_md", analysis_data.get("report", ""))
    chapters = analysis_data.get("chapters", [])
    statistics = analysis_data.get("statistics", {})

    lines: List[str] = [
        f"# {product_name} 评论深度分析报告",
        "",
        f"> 分析工具: Review Analyzer Skill V2.0",
        f"> 署名: {creator}",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 评论数: {summary.get('total', analysis_data.get('total_reviews', 'N/A'))}",
        "",
        "---",
        "",
    ]

    # 如果有 chapters 结构（新版格式），直接使用
    if chapters:
        for chapter in chapters:
            title = chapter.get("title", "")
            content = chapter.get("content", "")
            if title and content:
                lines.append(f"## {title}\n\n{content}\n\n")
    else:
        # 兼容旧版：从散装字段组装
        # 情感分布
        if sentiment:
            lines.append("## 情感分布\n")
            total = summary.get("total", 0)
            for label, count in sentiment.items():
                pct = (count / total * 100) if total > 0 else 0
                lines.append(f"- **{label}**: {count} 条 ({pct:.1f}%)")
            lines.append("")

        # 高频标签
        if top_tags:
            lines.append("## 高频标签\n")
            for i, (tag, count) in enumerate(list(top_tags.items())[:20], 1):
                lines.append(f"{i}. **{tag}**: {count} 次")
            lines.append("")

        # 用户画像
        if personas:
            lines.append("## 用户画像\n")
            for persona in personas:
                name = persona.get("name", "未知画像")
                count = persona.get("count", 0)
                lines.append(f"### {name} ({count} 条)\n")
                tags = persona.get("tags", {})
                for k, v in tags.items():
                    if v and v not in ("未提及", "不明", "无", ""):
                        lines.append(f"- {k}: {v}")
                lines.append("")

        # 洞察正文
        if insights_md:
            lines.append("## 深度洞察\n")
            lines.append(insights_md)
            lines.append("")

    # 统计数据
    if statistics:
        lines.append("## 数据统计\n")
        for key, value in statistics.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML 看板生成
# ---------------------------------------------------------------------------

def _write_html_dashboard(
    html_path: Path,
    analysis_data: dict,
    chart_configs: List[ChartConfig],
    template_name: str,
    asin: str,
    creator: str,
) -> None:
    """写入 HTML 可视化看板。

    Args:
        html_path: 输出文件路径
        analysis_data: 分析结果
        chart_configs: 图表配置列表
        template_name: 模板名称
        asin: 产品 ASIN
        creator: 署名
    """
    # 构建注入数据（合并到 analysis_data 供模板使用）
    injection_data = dict(analysis_data)
    injection_data.setdefault("asin", asin)
    injection_data.setdefault("creator", creator)

    try:
        html_content = render(template_name, injection_data, chart_configs)
        html_path.write_text(html_content, encoding="utf-8")
    except Exception as exc:
        logger.error("HTML 看板渲染失败: %s", exc)
        # 降级：写入一个简单的错误页面
        html_path.write_text(
            f"<html><body><h1>看板生成失败</h1><p>{exc}</p></body></html>",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# 模板选择
# ---------------------------------------------------------------------------

def select_template() -> str:
    """交互式模板选择。

    如果只有一个模板则自动选择；否则列出所有模板让用户选择。

    Returns:
        模板名称字符串。
    """
    templates = list_templates()

    if not templates:
        logger.warning("未发现任何模板，使用默认模板名称 'premium-gold'")
        return "premium-gold"

    if len(templates) == 1:
        name = templates[0]["name"]
        logger.info("仅有一个模板，自动选择: %s", name)
        return name

    # 交互式选择
    print("\n可用模板列表:")
    for i, tpl in enumerate(templates, 1):
        desc = tpl.get("description", "")
        print(f"  {i}. {tpl['name']} - {desc}")

    print(f"\n  输入编号选择（默认 1）: ", end="")

    try:
        choice = input().strip()
        if not choice:
            return templates[0]["name"]
        idx = int(choice) - 1
        if 0 <= idx < len(templates):
            return templates[idx]["name"]
    except (ValueError, EOFError):
        pass

    return templates[0]["name"]


# ---------------------------------------------------------------------------
# 核心接口 — 函数式 API
# ---------------------------------------------------------------------------

def generate_outputs(
    analysis_data: dict,
    output_config: Optional[dict] = None,
) -> dict:
    """编排所有输出通道，生成完整报告。

    执行以下步骤：
      1. 始终生成 Markdown 报告
      2. 始终生成 HTML 看板
      3. 可选同步到飞书（当 output_config 中 sync_feishu=True 时）

    Args:
        analysis_data: 分析结果字典，包含：
            - asin (str): 产品 ASIN
            - product_name (str): 产品名称
            - summary (dict): 统计摘要
            - sentiment / sentiment_distribution (dict): 情感分布
            - tag_statistics (dict): 标签统计
            - dimensional_stats (dict): 维度统计
            - top_tags (dict): 高频标签
            - personas (list): 用户画像
            - golden_samples (list): 黄金样本
            - insights_md (str): 洞察报告正文
        output_config: 输出配置，可选键：
            - template_name (str): 模板名称，默认自动选择
            - sync_feishu (bool): 是否同步飞书，默认 False
            - output_dir (str): 自定义输出目录
            - asin (str): 覆盖 analysis_data 中的 asin
            - creator (str): 报告署名

    Returns:
        {
            "md_path": str,
            "html_path": str,
            "feishu_result": dict,
            "charts": list,  # ChartConfig 序列化后的列表
        }
    """
    if output_config is None:
        output_config = {}

    asin = output_config.get("asin") or analysis_data.get("asin", "unknown")
    creator = output_config.get("creator", analysis_data.get("creator", "AI Assistant"))

    # 确定输出目录
    output_dir_str = output_config.get("output_dir")
    if output_dir_str:
        output_dir = Path(output_dir_str)
    else:
        output_dir = config.OUTPUT_DIR

    result: Dict[str, Any] = {
        "md_path": "",
        "html_path": "",
        "feishu_result": {
            "success": False,
            "doc_url": "",
            "whiteboard_urls": [],
            "whiteboard_count": 0,
            "error": "未执行飞书同步",
        },
        "charts": [],
    }

    logger.info("开始生成输出: ASIN=%s, output_dir=%s", asin, output_dir)

    # 1. 生成图表配置
    try:
        chart_configs = generate_all_charts(analysis_data)
        result["charts"] = [cc.to_dict() for cc in chart_configs]
        logger.info("图表配置生成完成: %d 个", len(chart_configs))
    except Exception as exc:
        logger.error("图表配置生成失败: %s", exc)
        chart_configs = []
        result["charts"] = []

    # 2. 生成 Markdown 报告
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / f"分析洞察报告_{asin}.md"
        md_content = _build_md_content(analysis_data, creator, asin)
        md_path.write_text(md_content, encoding="utf-8")
        result["md_path"] = str(md_path)
        logger.info("MD 报告已生成: %s", md_path)
    except Exception as exc:
        logger.error("Markdown 报告生成失败: %s", exc)

    # 3. 生成 HTML 看板
    try:
        template_name = output_config.get("template_name")
        if not template_name:
            templates = list_templates()
            template_name = templates[0]["name"] if templates else "premium-gold"

        html_path = output_dir / f"可视化洞察报告_{asin}.html"
        _write_html_dashboard(
            html_path, analysis_data, chart_configs, template_name, asin, creator
        )
        result["html_path"] = str(html_path)
        logger.info("HTML 看板已生成: %s", html_path)
    except Exception as exc:
        logger.error("HTML 看板生成失败: %s", exc)

    # 4. 可选：飞书同步
    if output_config.get("sync_feishu", False):
        try:
            from src.feishu_sync import sync_report

            # 读取已生成的 Markdown 内容
            md_content = ""
            if result["md_path"]:
                try:
                    md_content = Path(result["md_path"]).read_text(encoding="utf-8")
                except Exception:
                    md_content = analysis_data.get("insights_md", "")

            product_name = analysis_data.get("product_name", asin)
            title = f"{product_name} 评论深度分析报告"
            feishu_result = sync_report(title, md_content, chart_configs)
            result["feishu_result"] = feishu_result
        except Exception as exc:
            logger.error("飞书同步异常（不影响主流程）: %s", exc)
            result["feishu_result"] = {
                "success": False,
                "doc_url": "",
                "whiteboard_urls": [],
                "whiteboard_count": 0,
                "error": f"飞书同步异常: {exc}",
            }

    logger.info(
        "输出生成完成: md=%s, html=%s, feishu=%s",
        bool(result["md_path"]),
        bool(result["html_path"]),
        result["feishu_result"].get("success", False),
    )
    return result


# ---------------------------------------------------------------------------
# 向后兼容 — 类封装
# ---------------------------------------------------------------------------

class OutputManager:
    """输出管理器 — 统一管理所有输出通道（类封装，向后兼容）。"""

    def generate_outputs(
        self,
        analysis_data: Dict,
        output_dir: Path,
        asin: str,
        template_name: str = "premium-gold",
        feishu_sync: bool = False,
        creator: str = "AI Assistant",
    ) -> Dict:
        """生成所有输出文件。

        Args:
            analysis_data: 分析结果数据
            output_dir: 输出目录
            asin: 产品 ASIN
            template_name: 可视化模板名称
            feishu_sync: 是否同步到飞书
            creator: 报告署名

        Returns:
            输出结果字典。
        """
        return generate_outputs(
            analysis_data,
            output_config={
                "template_name": template_name,
                "sync_feishu": feishu_sync,
                "output_dir": str(output_dir),
                "asin": asin,
                "creator": creator,
            },
        )

    def select_template_interactive(self) -> str:
        """交互式模板选择。"""
        return select_template()

"""
HTML 报告生成模块 V1.0 - 黑金奢华看板
使用 Gemini API 生成专业决策级别的可视化 HTML 数据看板
严格按照 prompt_html.json 和 prompt_html.md 的规范生成
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys
import logging

try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from src.config import config, mask_api_key

# 配置日志
logger = logging.getLogger(__name__)


def _load_json_template() -> Dict:
    """加载 JSON 数据模板"""
    json_path = config.REFERENCES_DIR / "可视化看板prompt/prompt_html.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_system_prompt() -> str:
    """加载黑金奢华 HTML 生成系统提示词"""
    prompt_path = config.REFERENCES_DIR / "可视化看板prompt/prompt_html.md"
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _extract_html_from_response(response_text: str) -> str:
    """从 Gemini 响应中提取 HTML 代码"""
    # 尝试提取 html 代码块
    html_pattern = r'```html\s*(.*?)\s*```'
    match = re.search(html_pattern, response_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 尝试提取通用代码块
    code_pattern = r'```\s*(.*?)\s*```'
    match = re.search(code_pattern, response_text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if content.startswith('<') and ('</html>' in content or '</body>' in content):
            return content

    # 如果没有代码块，检查是否是纯 HTML
    if response_text.strip().startswith('<'):
        return response_text.strip()

    return response_text.strip()


def _extract_strategic_json(insights_md: Optional[str]) -> Dict:
    """从洞察报告中提取结构化战略 JSON (V1.0 核心逻辑)"""
    if not insights_md:
        return {}

    # 寻找 <strategic_json> 块
    pattern = r'<strategic_json>\s*(.*?)\s*</strategic_json>'
    match = re.search(pattern, insights_md, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception as e:
            print(f"   ⚠️  提取到的 strategic_json 解析失败: {e}")

    return {}


class ChartDataSentinel:
    """图表数据哨兵：处理小样本或缺失数据的优雅退化"""

    @staticmethod
    def validate_and_fill(data_obj: Dict, default_labels: List[str], min_items: int = 3) -> Optional[Dict]:
        """验证并填充图表数据，如果数据为空则返回 None"""
        labels = data_obj.get("labels", [])
        data = data_obj.get("data", [])
        count = data_obj.get("count", 0)

        # 如果数据为空或数量不足，返回 None（表示不渲染此图表）
        if not labels or not data or len(labels) == 0 or len(data) == 0 or count == 0:
            return None

        # 补全到 min_items (如果需要)
        while len(labels) < min_items and len(labels) < len(default_labels):
            idx = len(labels)
            labels.append(default_labels[idx])
            data.append(0)

        return {"labels": labels, "data": data, "count": count}


def _build_json_data(
    asin: str,
    product_name: Optional[str],
    summary: Optional[Dict],
    personas: Optional[List[Dict]],
    sentiment_distribution: Optional[Dict],
    tag_statistics: Optional[Dict],
    golden_samples: Optional[List[Dict]],
    insights_md: Optional[str],
    creator_name: str
) -> Dict:
    """构建符合 prompt_html.json 格式的数据结构"""

    template = _load_json_template()
    product = product_name or asin

    # ========== Meta 信息 ==========
    meta = {
        "product_name": product,
        "report_title": f"{product} 评论深度分析洞察",
        "signature": f"Created By {creator_name}",
        "retail_price": "待补充",
        "sample_size": str(summary.get("total", 0)) if summary else "0",
        "status": "Strategic Review"
    }

    # ========== KPI 指标 ==========
    # 从统计数据中提取 KPI（修复键名不匹配问题）
    total = summary.get("total", 0) if summary else 0
    tagged = summary.get("tagged", 0) if summary else 0

    # 计算平均评分（从 tag_statistics 中获取或使用默认值）
    avg_rating = 0
    if summary and "avg_rating" in summary:
        avg_rating = summary.get("avg_rating", 0)
    elif tag_statistics and "功能_满意度" in tag_statistics:
        # 如果没有 avg_rating，从满意度数据估算
        satisfaction = tag_statistics.get("功能_满意度", {})
        total_count = sum(satisfaction.values())
        if total_count > 0:
            # 简单加权：超出预期=5, 符合预期=4, 低于预期=2, 其他=3
            weights = {"超出预期": 5, "符合预期": 4, "低于预期": 2}
            weighted_sum = sum(count * weights.get(label, 3) for label, count in satisfaction.items())
            avg_rating = round(weighted_sum / total_count, 1)

    # 计算数据沉默率
    silence_rate = ((total - tagged) / total * 100) if total > 0 else 0

    kpis = [
        {
            "title": "Total Reviews",
            "value": str(total),
            "label": "总评论数",
            "desc": "样本量" + ("极低" if total < 50 else "充足" if total > 200 else "中等")
        },
        {
            "title": "Average Rating",
            "value": str(avg_rating),
            "label": "平均评分",
            "desc": "行业" + ("基准线以上" if avg_rating >= 4.0 else "基准线以下"),
            "is_danger": avg_rating < 3.5
        },
        {
            "title": "Data Silence Rate",
            "value": f"{silence_rate:.0f}",
            "label": "数据沉默率",
            "desc": "解析失败/无有效内容",
            "is_danger": silence_rate > 50
        },
        {
            "title": "Tagged Reviews",
            "value": str(tagged),
            "label": "已打标评论",
            "desc": f"成功率 {tagged/total*100:.0f}%" if total > 0 else "0%"
        }
    ]

    # ========== 提取结构化数据 (V1.0) ==========
    strategic_data = _extract_strategic_json(insights_md)

    # ========== 市场洞察 ==========
    market_insights = [
        {
            "icon": "fa-users",
            "title": "核心受众画像",
            "desc": _extract_insight_text(insights_md, ["受众", "用户", "人群", "画像"])
        },
        {
            "icon": "fa-hand-pointer",
            "title": "易用性评估",
            "desc": _extract_insight_text(insights_md, ["易用", "使用", "体验", "操作"])
        },
        {
            "icon": "fa-gift",
            "title": "购买场景特征",
            "desc": _extract_insight_text(insights_md, ["场景", "用途", "购买", "动机"])
        },
        {
            "icon": "fa-chess-knight",
            "title": "竞品威胁区隔",
            "desc": _extract_insight_text(insights_md, ["竞品", "对手", "差异化", "对比"])
        }
    ]

    # ========== 图表数据 (带哨兵保护) ==========
    # 构建所有图表数据，只保留有效数据
    charts_data_raw = {
        "sentiment": ChartDataSentinel.validate_and_fill(
            _build_chart_data(sentiment_distribution, ["强烈推荐", "推荐", "中立", "不推荐", "强烈不推荐"]),
            ["强烈推荐", "推荐", "中立", "不推荐", "强烈不推荐"]
        ),
        "features": ChartDataSentinel.validate_and_fill(
            _build_top_tags_data(tag_statistics, ["功能_", "卖点", "优势"]),
            ["核心性能", "耐用性", "设计美感"]
        ),
        "scenarios": ChartDataSentinel.validate_and_fill(
            _build_top_tags_data(tag_statistics, ["场景_", "用途", "使用"]),
            ["室内办公", "家庭生活", "户外作业"]
        ),
        "price_perception": ChartDataSentinel.validate_and_fill(
            _build_top_tags_data(tag_statistics, ["价格", "性价比", "贵", "便宜"], default_labels=["物超所值", "偏贵", "合理"]),
            ["超高性价比", "价格合理", "溢价较高"]
        ),
        "design_usability": ChartDataSentinel.validate_and_fill(
            _build_top_tags_data(tag_statistics, ["易用", "设计", "外观"], default_labels=["外观精美", "操作直观", "笨重", "复杂"]),
            ["工业设计", "UI易用性", "手感反馈"]
        ),
        "durability": ChartDataSentinel.validate_and_fill(
            _build_top_tags_data(tag_statistics, ["耐用", "质量", "材质", "寿命"], default_labels=["质量上乘", "材质优良", "易损耗"]),
            ["结构强度", "表面喷涂", "按键寿命"]
        )
    }

    # 过滤掉 None 值（空数据图表）
    charts_data = {k: v for k, v in charts_data_raw.items() if v is not None}

    # ========== 战略洞察 (优先用 JSON) ==========
    moat_pros = strategic_data.get("moat")
    if not moat_pros:
        moat_pros = _extract_strategy_items(insights_md, "护城河", "优势", "壁垒", "亮点")

    vulnerability_cons = strategic_data.get("vulnerability")
    if not vulnerability_cons:
        vulnerability_cons = _extract_strategy_items(insights_md, "软肋", "劣势", "缺陷", "痛点")

    # ========== 核心决策矩阵 (优先用 JSON) ==========
    execution_matrix = strategic_data.get("execution_matrix")
    if not execution_matrix:
        execution_matrix = _extract_execution_matrix(insights_md)

    # ========== 用户原声 (VOC) ==========
    voc_quotes = []

    # 尝试从 MD 中提取带头像类型的 VOC
    md_voc = _extract_voc_with_avatars(insights_md)
    if md_voc:
        voc_quotes = md_voc
    elif golden_samples:
        for sample in golden_samples[:4]:
            is_danger = sample.get("sentiment") in ["不推荐", "强烈不推荐"]
            # 基础映射逻辑
            avatar_type = "casual_lite"
            if "强烈推荐" in sample.get("sentiment", ""):
                avatar_type = "tech_expert"
            elif is_danger:
                avatar_type = "business_elite"

            voc_quotes.append({
                "profile": _get_user_profile(sample),
                "avatar_type": avatar_type,
                "quote": sample.get("body", "")[:300] + "..." if len(sample.get("body", "")) > 300 else sample.get("body", ""),
                "status": _get_user_status(sample),
                "is_danger": is_danger
            })

    if not voc_quotes:
        # 兜底
        voc_quotes = [
            {"profile": "Advocate / 技术大牛", "avatar_type": "tech_expert", "quote": "其工业设计与内部堆料确实达到了行业第一梯队水平...", "status": "High Loyalty", "is_danger": False},
            {"profile": "Detractor / 商务精英", "avatar_type": "business_elite", "quote": "在关键的会议场合出现了断连，这对于专业人士来说是不可接受的。", "status": "Trust Broken", "is_danger": True},
            {"profile": "Passive / 生活家", "avatar_type": "casual_lite", "quote": "平时用着还行，就是没什么特别惊艳的地方。", "status": "Neutral", "is_danger": False},
            {"profile": "Advocate / 极客玩家", "avatar_type": "tech_expert", "quote": "固件更新非常及时，这就是我选择该品牌的理由。", "status": "Premium Perception", "is_danger": False}
        ]

    # 组装完整数据
    return {
        "meta": meta,
        "kpis": kpis,
        "market_insights": market_insights,
        "charts_data": charts_data,
        "strategy": {
            "moat_pros": moat_pros if moat_pros else [{"title": "护城河缺失", "desc": "数据量不足，无法提取核心壁垒"}],
            "vulnerability_cons": vulnerability_cons if vulnerability_cons else [{"title": "风险点未知", "desc": "数据量不足，无法提取致命弱点"}]
        },
        "execution_matrix": execution_matrix if execution_matrix else [
            {"urgency": "Short-Term", "directive": "增加样本量", "details": "当前数据量过小，不足以支持核心决策", "roi": "数据可信度提升 100%"}
        ],
        "voc_quotes": voc_quotes
    }


def _extract_insight_text(insights_md: Optional[str], keywords: List[str]) -> str:
    """从洞察报告中提取相关文本"""
    if not insights_md:
        return "暂无相关数据..."

    lines = insights_md.split('\n')
    for line in lines:
        for keyword in keywords:
            if keyword in line:
                # 提取这一行和下一行
                idx = lines.index(line)
                result = line.replace("【.*?】", "").strip()
                if idx + 1 < len(lines):
                    result += " " + lines[idx + 1].strip()
                return result[:100] + "..." if len(result) > 100 else result
    return "暂无相关数据..."


def _build_chart_data(distribution: Optional[Dict], default_labels: List[str]) -> Dict:
    """构建图表数据"""
    if not distribution:
        return {"labels": [], "data": [], "count": 0}

    labels = list(distribution.keys())
    data = list(distribution.values())

    return {
        "labels": labels[:5],  # 最多5个
        "data": data[:5],
        "count": len(labels)
    }


def _build_top_tags_data(tag_statistics: Optional[Dict], keywords: List[str], default_labels: List[str] = None) -> Dict:
    """从标签统计中构建特定类别的图表数据"""
    if not tag_statistics:
        return {"labels": [], "data": [], "count": 0}

    # 筛选包含关键词的标签
    filtered = {}
    for tag, count in tag_statistics.items():
        for keyword in keywords:
            if keyword in tag:
                # 移除关键词前缀，简化标签名
                clean_label = tag.replace(keyword, "").replace("_", "").strip()
                if clean_label:
                    filtered[clean_label] = count
                break

    if not filtered:
        return {"labels": [], "data": [], "count": 0}

    # 按数量排序，取前5
    sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "labels": [item[0] for item in sorted_items],
        "data": [item[1] for item in sorted_items],
        "count": len(sorted_items)
    }


def _extract_strategy_items(insights_md: Optional[str], *keywords) -> List[Dict]:
    """从洞察报告中提取战略条目"""
    if not insights_md:
        return []

    result = []
    lines = insights_md.split('\n')

    for keyword_group in keywords:
        for i, line in enumerate(lines):
            if any(kw in line for kw in keyword_group):
                # 提取标题和描述
                title = line.replace("【.*?】", "").replace(">", "").strip()
                title = title[:50] + "..." if len(title) > 50 else title

                desc = ""
                if i + 1 < len(lines):
                    desc = lines[i + 1].strip()
                    desc = desc[:100] + "..." if len(desc) > 100 else desc

                if title and not any(item["title"] == title for item in result):
                    result.append({"title": title, "desc": desc})
                    if len(result) >= 4:
                        break

        if len(result) >= 4:
            break

    return result


def _extract_execution_matrix(insights_md: Optional[str]) -> List[Dict]:
    """从洞察报告中提取核心决策矩阵"""
    if not insights_md:
        return None

    result = []
    lines = insights_md.split('\n')

    urgency_map = {
        "immediate": "Immediate",
        "urgent": "Immediate",
        "短期": "Short-Term",
        "short": "Short-Term",
        "长期": "Long-Term",
        "long": "Long-Term"
    }

    # 寻找执行建议相关段落
    for i, line in enumerate(lines):
        line_lower = line.lower()
        urgency = None

        for kw, mapped in urgency_map.items():
            if kw in line_lower:
                urgency = mapped
                break

        if urgency:
            directive = line.replace("【.*?】", "").strip()
            directive = directive[:50] + "..." if len(directive) > 50 else directive

            # 提取后续的执行细节和ROI
            details = ""
            roi = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j].strip()
                if "执行" in next_line or "细节" in next_line or "行动" in next_line:
                    details = next_line[:100] + "..." if len(next_line) > 100 else next_line
                elif "ROI" in next_line or "预期" in next_line or "提升" in next_line:
                    roi = next_line[:100] + "..." if len(next_line) > 100 else next_line

            result.append({
                "urgency": urgency,
                "directive": directive,
                "details": details or "执行细节...",
                "roi": roi or "预期ROI..."
            })

            if len(result) >= 3:
                break

    return result if result else None


def _extract_voc_with_avatars(insights_md: str) -> List[Dict]:
    """从 MD 中提取带有 3D 头像及深度详情的 VOC 数据 (V1.0)"""
    if not insights_md:
        return []

    result = []
    # 寻找 ## 六、典型用户深度解析 (VOC) 之后的块
    if "## 六、典型用户深度解析" not in insights_md:
        return []

    voc_section = insights_md.split("## 六、典型用户深度解析")[1].split("## ")[0]
    blocks = voc_section.split("**典型画像**：")

    for block in blocks[1:]: # 第一个是标题前的内容
        try:
            # 1. 典型画像
            profile = block.split("\n")[0].strip()

            # 2. 头像类型
            avatar_type = "male_young" # 默认值
            if "**头像类型**：" in block:
                avatar_val = block.split("**头像类型**：")[1].split("\n")[0].strip().lower()
                # 语义清理
                for t in ["male_young", "female_young", "male_elderly", "female_elderly", "child_boy", "child_girl"]:
                    if t in avatar_val:
                        avatar_type = t
                        break

            # 3. 核心需求
            core_need = "暂无需求提取"
            if "**核心需求**：" in block:
                core_need = block.split("**核心需求**：")[1].split("\n")[0].strip()

            # 4. 评价原文
            quote = ""
            if "**评价原文**：" in block:
                quote = block.split("**评价原文**：")[1].split("\n")[0].strip().strip('"')

            # 5. 评论解析
            analysis = ""
            if "**评论解析**：" in block:
                analysis = block.split("**评论解析**：")[1].split("\n")[0].strip()

            # 状态判定
            status = "Neutral Observer"
            is_danger = False
            if "强烈推荐" in profile or "强推" in profile or "惊喜" in block:
                status = "High Satisfaction"
            elif "强烈不推荐" in profile or "差评" in profile or "质量" in block:
                status = "Trust Broken"
                is_danger = True

            result.append({
                "profile": profile,           # 画像描述
                "avatar_type": avatar_type,   # 6种类型之一
                "core_need": core_need,       # 核心需求
                "quote": quote,               # 原生评论
                "analysis": analysis,         # 深度解读
                "status": status,
                "is_danger": is_danger
            })
        except Exception as e:
            continue

    return result[:4]


def _get_user_profile(sample: Dict) -> str:
    """获取用户画像描述"""
    body = sample.get("body", "")
    sentiment = sample.get("sentiment", "中立")
    rating = sample.get("rating", 0)

    # 根据情感和评分推断
    if rating >= 4:
        return f"满意用户 / Advocate"
    elif rating <= 2:
        return f"流失风险 / Detractor"
    elif sentiment == "中立":
        return f"观望用户 / Passive"
    else:
        return f"普通用户 / Neutral"


def _render_with_jinja2(
    asin: str,
    json_data: Dict,
    insights_md: str,
    output_path: Path
) -> None:
    """使用 Jinja2 本地渲染 HTML (降级方案)"""
    if not JINJA2_AVAILABLE:
        raise ImportError("❌ 未安装 jinja2，无法进行本地渲染。请运行: pip install jinja2")

    template_path = config.template_path
    if not template_path.exists():
        raise FileNotFoundError(f"❌ 找不到 HTML 模板: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # 准备模板数据
    total_reviews = int(json_data.get("meta", {}).get("sample_size", 0))

    # 从KPI数据中提取平均评分
    kpis = json_data.get("kpis", [])
    avg_rating = 4.5  # 默认值
    for kpi in kpis:
        if kpi.get("title") == "Average Rating":
            try:
                avg_rating = float(kpi.get("value", 4.5))
            except (ValueError, TypeError):
                avg_rating = 4.5
            break

    template_vars = {
        "asin": asin,
        "product_name": json_data.get("meta", {}).get("product_name", asin),
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "total_reviews": total_reviews,
            "tagged_reviews": total_reviews, # 本地模式默认全显示
            "persona_count": len(json_data.get("personas", [])),
            "avg_rating": avg_rating  # 从KPI数据中提取
        },
        "personas": json_data.get("personas", []),
        "sentiment_distribution": json_data.get("sentiment_distribution", {}),
        "tag_statistics": json_data.get("tag_statistics", {}),
        "golden_samples": json_data.get("golden_samples", []),
        "insights_md": insights_md,
    }

    # 渲染
    template = jinja2.Template(template_content)
    html_content = template.render(**template_vars)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def _get_user_status(sample: Dict) -> str:
    """获取用户状态"""
    sentiment = sample.get("sentiment", "")
    rating = sample.get("rating", 0)

    if "强烈推荐" in sentiment or rating >= 5:
        return "High Satisfaction"
    elif "强烈不推荐" in sentiment or rating <= 2:
        return "Trust Broken"
    elif "推荐" in sentiment or rating >= 4:
        return "Premium Perception"
    else:
        return "Neutral Observer"


def generate_html_report(
    asin: str,
    product_name: Optional[str] = None,
    summary: Optional[Dict] = None,
    personas: Optional[List[Dict]] = None,
    sentiment_distribution: Optional[Dict] = None,
    tag_statistics: Optional[Dict] = None,
    golden_samples: Optional[List[Dict]] = None,
    insights_md: Optional[str] = None,
    creator_name: str = "Gemini-1.5-Pro",
) -> Path:
    """生成黑金奢华可视化 HTML 报告"""
    output_path = config.get_html_path(asin)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 提取结构化数据 (用于分析源)
    _ = _extract_strategic_json(insights_md)
    
    # 2. 清洗 insights_md (剥离 strategic_json 块供前端展示)
    clean_md = insights_md or ""
    if "<strategic_json>" in clean_md:
        clean_md = re.sub(r'<strategic_json>.*?</strategic_json>', '', clean_md, flags=re.DOTALL).strip()

    # 3. 准备共用的 json_data
    json_data = _build_json_data(
        asin=asin, product_name=product_name, summary=summary,
        personas=personas, sentiment_distribution=sentiment_distribution,
        tag_statistics=tag_statistics, golden_samples=golden_samples,
        insights_md=clean_md, creator_name=creator_name
    )

    # 4. 模式判定：如果显式指定 local 或没有 API Key，直接走本地渲染
    if config.HTML_GENERATION_SOURCE == "local" or not config.GEMINI_API_KEY:
        print(f"   💡 进入「本地经典模式」生成可视化看板...")
        _render_with_jinja2(asin, json_data, clean_md, output_path)
        return output_path

    # 5. 尝试使用 Gemini 生成 (高品质生成式渲染)
    print(f"   🎨 使用 Gemini {config.HTML_GENERATION_MODEL} 生成黑金奢华看板...")
    try:
        if not GEMINI_AVAILABLE:
            raise RuntimeError("google-generativeai 未安装")

        # 安全地记录API Key配置（仅显示后4位）
        logger.debug(f"配置 Gemini API Key: {mask_api_key(config.GEMINI_API_KEY)}")
        genai.configure(api_key=config.GEMINI_API_KEY)
        system_prompt = _load_system_prompt()
        if not system_prompt:
            raise RuntimeError("找不到 prompt_html.md")

        system_prompt = system_prompt.replace("{CREATOR_NAME}", creator_name)

        full_prompt = f"# JSON 数据输入\n\n```json\n{json.dumps(json_data, ensure_ascii=False, indent=2)}\n```\n\n# 产品名称\n{product_name or asin}\n\n# 报告原文\n{clean_md}\n"

        model = genai.GenerativeModel(
            model_name=config.HTML_GENERATION_MODEL,
            system_instruction=system_prompt
        )

        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=config.HTML_GENERATION_TEMPERATURE,
                max_output_tokens=16384,
            )
        )

        html_content = _extract_html_from_response(response.text)
        if not html_content or len(html_content) < 500:
            raise ValueError("Gemini 生成的 HTML 异常")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"   ✅ HTML 报告生成成功: {output_path.name}")
        return output_path

    except Exception as e:
        print(f"   ⚠️ Gemini 渲染故障 ({e})，正在自动退位至「本地经典模式」...")
        _render_with_jinja2(asin, json_data, clean_md, output_path)
        return output_path

# ========== 保留的辅助函数（向后兼容） ==========

def get_sentiment_class(sentiment: str) -> str:
    """获取情感对应的 CSS 类名（保留用于向后兼容）"""
    return {
        "强烈推荐": "strong-positive",
        "推荐": "positive",
        "中立": "neutral",
        "不推荐": "negative",
        "强烈不推荐": "strong-negative",
    }.get(sentiment, "neutral")


def validate_report_data(
    asin: str,
    summary: Optional[Dict] = None,
    personas: Optional[List[Dict]] = None,
    sentiment_distribution: Optional[Dict] = None,
    tag_statistics: Optional[Dict] = None,
    golden_samples: Optional[List[Dict]] = None,
) -> Dict[str, bool]:
    """验证报告数据的完整性"""
    return {
        "asin_valid": bool(asin and isinstance(asin, str)),
        "summary_valid": bool(summary and isinstance(summary, dict)),
        "personas_valid": bool(personas and isinstance(personas, list)),
        "sentiment_valid": bool(sentiment_distribution and isinstance(sentiment_distribution, dict)),
        "tags_valid": bool(tag_statistics and isinstance(tag_statistics, dict)),
        "samples_valid": bool(golden_samples and isinstance(golden_samples, list)),
    }

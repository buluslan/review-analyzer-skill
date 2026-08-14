"""
异常信号检测器 V1.0

确定性规则引擎，从已打标评论的 22 维标签中自动检测异常信号，
输出严重度分级的决策卡数据。

零 LLM 成本、零外部数据源、纯 Python 确定性计算。
检测结果注入报告 prompt（供 AI 渲染成 prose 卡片），并同步到
strategic_json.anomaly_cards 数据通道（template_engine 消费）。

规则覆盖 5 类异常：
  1. 高分低情隐性流失（rating>=4 但情感负面/中立）
  2. 质量隐患集中（材质差/做工粗糙/易坏）
  3. 退货售后集中爆发（退换货困难/客服迟缓/无保修/包装破损）
  4. 负面突增（近 30 天负面率 vs 基线，需日期数据）
  5. 复购流失预警（不会复购 + 价格偏贵叠加升级）
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ==================== 常量定义 ====================

_NEGATIVE_SENTIMENTS: Set[str] = {"不推荐", "强烈不推荐"}
_NEUTRAL_SENTIMENT: str = "中立"

# 严重度等级
_SEVERITY_HIGH = "高"
_SEVERITY_MID = "中"
_SEVERITY_LOW = "低"

# 噪声值（不计入有效命中）
_NOISE_VALUES: Set[str] = {"不明", "未提及", "无", "未知", "不明确", "其他"}


# ==================== 数据结构 ====================


@dataclass
class AnomalySignal:
    """单条异常信号。

    Attributes:
        signal_type: 信号类型名称（如"高分低情隐性流失"）
        severity: 严重度（高/中/低）
        affected_count: 命中条数
        affected_pct: 命中占比（0-100）
        source_tags: 涉及的标签维度列表
        representative_quotes: 代表性用户原话（最多 3 条）
        suggested_action: 建议动作
        detail: 补充细节（如子维度分布、基线对比值等）
    """

    signal_type: str
    severity: str
    affected_count: int
    affected_pct: float
    source_tags: List[str]
    representative_quotes: List[str] = field(default_factory=list)
    suggested_action: str = ""
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典（供 strategic_json / 看板使用）。"""
        return asdict(self)


# ==================== 预设动作模板 ====================

_ACTION_TEMPLATES: Dict[str, str] = {
    "高分低情隐性流失": (
        "紧急排查高分评论中的负面情感根因。重点检查是否存在"
        "「货不对板」「预期落差」「隐性缺陷」问题。建议在 Listing "
        "中诚实描述产品边界，避免过度承诺导致预期落差。详见第十章情感背离分析。"
    ),
    "质量隐患集中": (
        "产品力根因排查。建议优先定位最集中的质量子维度"
        "（材质/做工/耐用性），与供应链联动做品质升级。"
        "质量隐患直接影响退货率和差评率，需在下次备货前完成改进。"
    ),
    "退货售后集中爆发": (
        "售后服务链路排查。退货困难直接吞噬利润，"
        "建议优化退换货流程（降低门槛、提升时效），"
        "同时排查客服响应速度和包装质量，减少售后触发的负面评价。"
    ),
    "负面突增": (
        "口碑恶化预警。建议立即排查近期是否有产品批次变更、"
        " Listing 修改、竞品动作或外部差评事件。"
        "近 30 天负面率显著高于基线，需要快速定位原因并干预。详见第九章时间趋势。"
    ),
    "复购流失预警": (
        "复购策略排查。「不会复购」占比偏高意味着用户留存断层。"
        "建议分析不复购用户的归因（价格/质量/体验），"
        "针对性优化核心价值主张，提升首次体验满意度。"
    ),
}


# ==================== 核心检测函数 ====================


def detect_anomalies(
    tagged_reviews: List[Dict[str, Any]],
    stats: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> List[AnomalySignal]:
    """异常信号检测主入口。

    从已打标评论数据中，按 5 条确定性规则检测异常信号，
    输出按严重度降序排列的 AnomalySignal 列表。

    Args:
        tagged_reviews: 已打标评论列表，每条含 rating/sentiment/tags/date 等字段
        stats: 统计摘要（可选，复用 dimensional_stats 避免重算）
        context: 条件上下文（可选），支持:
            - has_review_date (bool): 是否有评论日期，控制负面突增规则
            - 其他字段会被忽略

    Returns:
        AnomalySignal 列表，按严重度（高>中>低）和命中条数降序排列。
        无异常时返回空列表。

    Example:
        >>> reviews = [{"rating": 4, "sentiment": "不推荐", "tags": {}, "body": "..."}]
        >>> signals = detect_anomalies(reviews)
        >>> len(signals)
        0  # 仅 1 条不触发阈值
    """
    if not tagged_reviews:
        logger.info("异常检测跳过：无评论数据")
        return []

    context = context or {}
    stats = stats or {}
    total = len(tagged_reviews)
    dimensional_stats = stats.get("dimensional_stats", {})

    signals: List[AnomalySignal] = []

    # 规则 1: 高分低情隐性流失
    sig = _detect_sentiment_gap(tagged_reviews, total)
    if sig:
        signals.append(sig)

    # 规则 2: 质量隐患集中
    sig = _detect_quality_issues(tagged_reviews, dimensional_stats, total)
    if sig:
        signals.append(sig)

    # 规则 3: 退货售后集中爆发
    sig = _detect_after_sales_issues(tagged_reviews, dimensional_stats, total)
    if sig:
        signals.append(sig)

    # 规则 4: 负面突增（需日期数据）
    if context.get("has_review_date", False):
        sig = _detect_negative_surge(tagged_reviews, total)
        if sig:
            signals.append(sig)
    else:
        # 降级：只报当前负面率绝对值
        sig = _detect_negative_absolute(tagged_reviews, total)
        if sig:
            signals.append(sig)

    # 规则 5: 复购流失预警
    sig = _detect_repurchase_churn(tagged_reviews, dimensional_stats, total)
    if sig:
        signals.append(sig)

    # 排序：严重度降序 + 命中条数降序
    severity_order = {_SEVERITY_HIGH: 0, _SEVERITY_MID: 1, _SEVERITY_LOW: 2}
    signals.sort(key=lambda s: (severity_order.get(s.severity, 9), -s.affected_count))

    logger.info(
        "异常检测完成: %d 条评论，检测到 %d 条信号 (%s)",
        total,
        len(signals),
        ", ".join(f"{s.signal_type}[{s.severity}]" for s in signals) or "无异常",
    )

    return signals


# ==================== 规则实现 ====================


def _get_rating(review: Dict[str, Any]) -> int:
    """安全提取评分，返回 0 表示无效。"""
    try:
        r = review.get("rating")
        if r is None:
            return 0
        return int(float(r))
    except (ValueError, TypeError):
        return 0


def _get_tags(review: Dict[str, Any]) -> Dict[str, Any]:
    """安全提取 tags 字典。"""
    tags = review.get("tags", {})
    if isinstance(tags, dict):
        return tags
    return {}


def _get_body(review: Dict[str, Any]) -> str:
    """安全提取评论正文。"""
    return str(review.get("body", "") or "").strip()


def _extract_quotes(reviews: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    """从命中评论中提取代表性原话（取正文最长的前 N 条）。"""
    candidates = []
    for r in reviews:
        body = _get_body(r)
        if body and len(body) >= 10:
            candidates.append(body)

    # 按长度降序，取前 limit 条，每条截断到 200 字
    candidates.sort(key=len, reverse=True)
    quotes = []
    for body in candidates[:limit]:
        if len(body) > 200:
            body = body[:197] + "..."
        quotes.append(body)
    return quotes


def _detect_sentiment_gap(
    tagged_reviews: List[Dict[str, Any]],
    total: int,
) -> Optional[AnomalySignal]:
    """规则 1: 高分低情隐性流失。

    命中条件：
      - rating>=4 且 (sentiment 为负面 或 tags.情感_总体评价 为负面)
      - rating>=4 且 sentiment==中立（弱信号）

    严重度：
      - 占比>=10% 或 N>=8 → 高
      - 占比 5%-10% → 中
      - 占比 2%-5% → 低
      - <2% 不触发
    """
    matched: List[Dict[str, Any]] = []

    for review in tagged_reviews:
        rating = _get_rating(review)
        if rating < 4:
            continue

        sentiment = review.get("sentiment", "")
        tags = _get_tags(review)
        overall = tags.get("情感_总体评价", "")

        # 强信号：高分 + 负面情感
        if sentiment in _NEGATIVE_SENTIMENTS or overall in _NEGATIVE_SENTIMENTS:
            matched.append(review)
        # 弱信号：高分 + 中立
        elif sentiment == _NEUTRAL_SENTIMENT:
            matched.append(review)

    count = len(matched)
    if count == 0:
        return None

    pct = count / total * 100

    # 阈值判断（<2% 不触发）
    if pct < 2 and count < 2:
        return None

    if pct >= 10 or count >= 8:
        severity = _SEVERITY_HIGH
    elif pct >= 5:
        severity = _SEVERITY_MID
    elif pct >= 2:
        severity = _SEVERITY_LOW
    else:
        return None

    quotes = _extract_quotes(matched)

    return AnomalySignal(
        signal_type="高分低情隐性流失",
        severity=severity,
        affected_count=count,
        affected_pct=round(pct, 1),
        source_tags=["rating", "sentiment", "情感_总体评价"],
        representative_quotes=quotes,
        suggested_action=_ACTION_TEMPLATES["高分低情隐性流失"],
        detail="高分（>=4星）评论中存在负面或中立情感，属于隐性流失信号。",
    )


def _detect_quality_issues(
    tagged_reviews: List[Dict[str, Any]],
    dimensional_stats: Dict[str, Dict[str, int]],
    total: int,
) -> Optional[AnomalySignal]:
    """规则 2: 质量隐患集中。

    命中集合（去重）：
      - tags.质量_材质==差
      - tags.质量_做工==粗糙
      - tags.质量_耐用性==易坏

    严重度：
      - 占比>=15% 或 N>=10 → 高
      - 占比 8%-15% → 中
      - 占比 3%-8% → 低
      - <3% 不触发
    """
    # 命中的 review id 集合（去重）
    matched_ids: Set[str] = set()
    matched_reviews: List[Dict[str, Any]] = []

    # 子维度计数
    sub_dim_counts: Dict[str, int] = {
        "质量_材质:差": 0,
        "质量_做工:粗糙": 0,
        "质量_耐用性:易坏": 0,
    }

    for i, review in enumerate(tagged_reviews):
        tags = _get_tags(review)
        review_id = review.get("review_id", str(i))
        hit = False

        if tags.get("质量_材质") == "差":
            sub_dim_counts["质量_材质:差"] += 1
            hit = True
        if tags.get("质量_做工") == "粗糙":
            sub_dim_counts["质量_做工:粗糙"] += 1
            hit = True
        if tags.get("质量_耐用性") == "易坏":
            sub_dim_counts["质量_耐用性:易坏"] += 1
            hit = True

        if hit and review_id not in matched_ids:
            matched_ids.add(review_id)
            matched_reviews.append(review)

    count = len(matched_reviews)
    if count == 0:
        return None

    pct = count / total * 100

    if pct < 3 and count < 3:
        return None

    if pct >= 15 or count >= 10:
        severity = _SEVERITY_HIGH
    elif pct >= 8:
        severity = _SEVERITY_MID
    elif pct >= 3:
        severity = _SEVERITY_LOW
    else:
        return None

    # 找出最集中的子维度
    top_sub = max(sub_dim_counts, key=sub_dim_counts.get)
    detail_parts = [
        f"子维度分布: {', '.join(f'{k}={v}条' for k, v in sub_dim_counts.items() if v > 0)}",
        f"最集中: {top_sub}",
    ]

    quotes = _extract_quotes(matched_reviews)

    return AnomalySignal(
        signal_type="质量隐患集中",
        severity=severity,
        affected_count=count,
        affected_pct=round(pct, 1),
        source_tags=["质量_材质", "质量_做工", "质量_耐用性"],
        representative_quotes=quotes,
        suggested_action=_ACTION_TEMPLATES["质量隐患集中"],
        detail="；".join(detail_parts),
    )


def _detect_after_sales_issues(
    tagged_reviews: List[Dict[str, Any]],
    dimensional_stats: Dict[str, Dict[str, int]],
    total: int,
) -> Optional[AnomalySignal]:
    """规则 3: 退货售后集中爆发。

    命中集合（去重）：
      - tags.服务_退换货==困难
      - tags.服务_客服响应==迟缓
      - tags.服务_保修==无保修
      - tags.服务_包装质量==破损

    严重度：
      - 服务_退换货==困难 占比>=8% → 高
      - 售后命中集合占比>=12% → 中
      - >=5% → 低
      - 更低不触发
    """
    matched_ids: Set[str] = set()
    matched_reviews: List[Dict[str, Any]] = []
    return_count = 0  # 退换货困难单独计数

    for i, review in enumerate(tagged_reviews):
        tags = _get_tags(review)
        review_id = review.get("review_id", str(i))
        hit = False

        if tags.get("服务_退换货") == "困难":
            return_count += 1
            hit = True
        if tags.get("服务_客服响应") == "迟缓":
            hit = True
        if tags.get("服务_保修") == "无保修":
            hit = True
        if tags.get("服务_包装质量") == "破损":
            hit = True

        if hit and review_id not in matched_ids:
            matched_ids.add(review_id)
            matched_reviews.append(review)

    count = len(matched_reviews)
    if count == 0:
        return None

    pct = count / total * 100
    return_pct = return_count / total * 100

    # 严重度判断（退货困难优先判高）
    if return_pct >= 8:
        severity = _SEVERITY_HIGH
    elif pct >= 12:
        severity = _SEVERITY_MID
    elif pct >= 5:
        severity = _SEVERITY_LOW
    else:
        return None

    detail_parts = [f"售后命中集合: {count}条({pct:.1f}%)"]
    if return_count > 0:
        detail_parts.append(f"退换货困难: {return_count}条({return_pct:.1f}%)")

    quotes = _extract_quotes(matched_reviews)

    return AnomalySignal(
        signal_type="退货售后集中爆发",
        severity=severity,
        affected_count=count,
        affected_pct=round(pct, 1),
        source_tags=["服务_退换货", "服务_客服响应", "服务_保修", "服务_包装质量"],
        representative_quotes=quotes,
        suggested_action=_ACTION_TEMPLATES["退货售后集中爆发"],
        detail="；".join(detail_parts),
    )


def _parse_date(date_str: str) -> Optional[datetime]:
    """解析日期字符串，支持常见格式。"""
    if not date_str or date_str in ("", "nan", "None", "null"):
        return None
    date_str = str(date_str).strip()

    # 常见日期格式
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:19] if "T" in date_str or " " in date_str else date_str[:10], fmt)
        except (ValueError, TypeError):
            continue

    # 尝试 ISO 格式
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _detect_negative_surge(
    tagged_reviews: List[Dict[str, Any]],
    total: int,
) -> Optional[AnomalySignal]:
    """规则 4a: 负面突增（有日期数据）。

    近 30 天 vs 基线（前 60 天），负面率差值：
      - >=20pp → 高
      - 10-20pp → 中
      - 8-10pp → 低
      - <8pp 或 近期样本<10 不触发
    """
    now = datetime.now()
    cutoff_30 = now - timedelta(days=30)
    cutoff_90 = now - timedelta(days=90)

    recent_reviews: List[Dict[str, Any]] = []
    baseline_reviews: List[Dict[str, Any]] = []

    for review in tagged_reviews:
        date_str = review.get("date", "")
        dt = _parse_date(str(date_str))
        if dt is None:
            continue

        if dt >= cutoff_30:
            recent_reviews.append(review)
        elif dt >= cutoff_90:
            baseline_reviews.append(review)

    # 近期样本不足，不触发
    if len(recent_reviews) < 10:
        logger.debug(
            "负面突增检测跳过：近 30 天样本不足 (%d<10)",
            len(recent_reviews),
        )
        return None

    # 基线样本不足时，用全部更早数据
    if len(baseline_reviews) < 5:
        for review in tagged_reviews:
            date_str = review.get("date", "")
            dt = _parse_date(str(date_str))
            if dt is not None and dt < cutoff_30 and review not in baseline_reviews:
                baseline_reviews.append(review)

    if not baseline_reviews:
        return None

    def _neg_rate(reviews: List[Dict[str, Any]]) -> float:
        """计算负面率。"""
        if not reviews:
            return 0.0
        neg = sum(
            1 for r in reviews
            if r.get("sentiment", "") in _NEGATIVE_SENTIMENTS
            or _get_tags(r).get("情感_总体评价", "") in _NEGATIVE_SENTIMENTS
        )
        return neg / len(reviews) * 100

    recent_neg = _neg_rate(recent_reviews)
    baseline_neg = _neg_rate(baseline_reviews)
    diff = recent_neg - baseline_neg

    if diff < 8:
        return None

    if diff >= 20:
        severity = _SEVERITY_HIGH
    elif diff >= 10:
        severity = _SEVERITY_MID
    else:
        severity = _SEVERITY_LOW

    # 命中评论 = 近期负面评论
    matched = [
        r for r in recent_reviews
        if r.get("sentiment", "") in _NEGATIVE_SENTIMENTS
        or _get_tags(r).get("情感_总体评价", "") in _NEGATIVE_SENTIMENTS
    ]
    quotes = _extract_quotes(matched)

    detail = (
        f"近期(30天)负面率 {recent_neg:.1f}% vs 基线 {baseline_neg:.1f}%，"
        f"差值 +{diff:.1f}pp；近期样本 {len(recent_reviews)} 条，基线样本 {len(baseline_reviews)} 条"
    )

    return AnomalySignal(
        signal_type="负面突增",
        severity=severity,
        affected_count=len(matched),
        affected_pct=round(recent_neg, 1),
        source_tags=["sentiment", "date"],
        representative_quotes=quotes,
        suggested_action=_ACTION_TEMPLATES["负面突增"],
        detail=detail,
    )


def _detect_negative_absolute(
    tagged_reviews: List[Dict[str, Any]],
    total: int,
) -> Optional[AnomalySignal]:
    """规则 4b: 负面突增降级版（无日期数据）。

    无日期时只报当前负面率绝对值：
      - >=30% → 高
      - 其余不触发
    """
    neg_count = sum(
        1 for r in tagged_reviews
        if r.get("sentiment", "") in _NEGATIVE_SENTIMENTS
        or _get_tags(r).get("情感_总体评价", "") in _NEGATIVE_SENTIMENTS
    )
    neg_pct = neg_count / total * 100 if total > 0 else 0

    if neg_pct < 30:
        return None

    matched = [
        r for r in tagged_reviews
        if r.get("sentiment", "") in _NEGATIVE_SENTIMENTS
        or _get_tags(r).get("情感_总体评价", "") in _NEGATIVE_SENTIMENTS
    ]
    quotes = _extract_quotes(matched)

    return AnomalySignal(
        signal_type="负面突增",
        severity=_SEVERITY_HIGH,
        affected_count=neg_count,
        affected_pct=round(neg_pct, 1),
        source_tags=["sentiment"],
        representative_quotes=quotes,
        suggested_action=_ACTION_TEMPLATES["负面突增"],
        detail=f"无日期数据，降级为绝对值判断：当前负面率 {neg_pct:.1f}%（>=30%阈值）",
    )


def _detect_repurchase_churn(
    tagged_reviews: List[Dict[str, Any]],
    dimensional_stats: Dict[str, Dict[str, int]],
    total: int,
) -> Optional[AnomalySignal]:
    """规则 5: 复购流失预警。

    命中 = tags.复购_复购意愿==不会
    严重度：
      - 占比>=15% → 高
      - 8-15% → 中
      - 3-8% → 低
      - <3% 不触发
    叠加：体验_价格感知==偏贵 占比>=10% → 自动升一级
    """
    matched: List[Dict[str, Any]] = []

    for review in tagged_reviews:
        tags = _get_tags(review)
        if tags.get("复购_复购意愿") == "不会":
            matched.append(review)

    count = len(matched)
    if count == 0:
        return None

    pct = count / total * 100

    if pct < 3:
        return None

    if pct >= 15:
        severity = _SEVERITY_HIGH
    elif pct >= 8:
        severity = _SEVERITY_MID
    else:
        severity = _SEVERITY_LOW

    # 叠加价格偏贵 → 升一级
    price_data = dimensional_stats.get("体验_价格感知", {})
    price_total = sum(price_data.values()) if price_data else 0
    price_expensive_pct = 0.0
    if price_total > 0:
        expensive_count = price_data.get("偏贵", 0)
        price_expensive_pct = expensive_count / price_total * 100

    if price_expensive_pct >= 10:
        severity_order = {_SEVERITY_LOW: 0, _SEVERITY_MID: 1, _SEVERITY_HIGH: 2}
        severity = (
            _SEVERITY_HIGH
            if severity_order[severity] >= 1
            else _SEVERITY_MID
        )
        severity_label = severity
    else:
        severity_label = severity

    detail_parts = [f"不会复购: {count}条({pct:.1f}%)"]
    if price_expensive_pct >= 10:
        detail_parts.append(
            f"叠加体验_价格感知==偏贵 {price_expensive_pct:.1f}%>=10%，严重度升级"
        )

    quotes = _extract_quotes(matched)

    return AnomalySignal(
        signal_type="复购流失预警",
        severity=severity_label,
        affected_count=count,
        affected_pct=round(pct, 1),
        source_tags=["复购_复购意愿", "体验_价格感知"],
        representative_quotes=quotes,
        suggested_action=_ACTION_TEMPLATES["复购流失预警"],
        detail="；".join(detail_parts),
    )


# ==================== 渲染辅助函数 ====================


def render_anomaly_signals_for_prompt(signals: List[AnomalySignal]) -> str:
    """将异常信号列表序列化为 markdown bullet 文本，供报告 prompt 注入。

    Args:
        signals: AnomalySignal 列表

    Returns:
        Markdown 格式的信号摘要文本。无信号时返回占位说明。
    """
    if not signals:
        return "本次未检测到异常信号（所有规则阈值未触发，数据健康）。"

    lines: List[str] = []
    severity_emoji = {_SEVERITY_HIGH: "🔴", _SEVERITY_MID: "🟠", _SEVERITY_LOW: "🟡"}

    for i, sig in enumerate(signals, 1):
        emoji = severity_emoji.get(sig.severity, "⚪")
        lines.append(f"**信号 {i}: {sig.signal_type}** {emoji} [{sig.severity}]")
        lines.append(f"  - 命中: {sig.affected_count} 条（占比 {sig.affected_pct}%）")
        lines.append(f"  - 来源标签: {', '.join(sig.source_tags)}")
        if sig.detail:
            lines.append(f"  - 详情: {sig.detail}")
        if sig.representative_quotes:
            for q in sig.representative_quotes[:2]:
                lines.append(f'  - 代表原话: "{q}"')
        if sig.suggested_action:
            lines.append(f"  - 建议动作: {sig.suggested_action}")
        lines.append("")

    return "\n".join(lines)

# -*- coding: utf-8 -*-
"""anomaly_detector.detect_anomalies 规则引擎回归测试。

覆盖 5 条规则：高分低情隐性流失 / 质量隐患集中 / 退货售后集中爆发 /
负面突增（有日期版 + 无日期降级版）/ 复购流失预警。
断言触发条件、严重度分级（高/中/低阈值边界）、无异常返回空列表、
结果按严重度降序排列。
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.anomaly_detector import detect_anomalies  # noqa: E402

LONG_BODY = "这是一条足够长的评论正文，用于满足代表性原话的最小长度要求。"
SHORT_BODY = "ok"


def make_review(
    rid,
    rating=5,
    sentiment="推荐",
    tags=None,
    date=None,
    body=LONG_BODY,
):
    """按 anomaly_detector 输入约定构造单条已打标评论。"""
    return {
        "review_id": rid,
        "rating": rating,
        "sentiment": sentiment,
        "tags": tags or {},
        "date": date or "",
        "body": body,
    }


def make_batch(n, **kwargs):
    """构造 n 条同配置评论，review_id 自动编号 r000/r001/..."""
    return [make_review(f"r{i:03d}", **kwargs) for i in range(n)]


def find(signals, signal_type):
    """按信号类型取检测结果。"""
    for s in signals:
        if s.signal_type == signal_type:
            return s
    return None


# ==================== 通用行为 ====================


def test_empty_input_returns_empty():
    assert detect_anomalies([]) == []


def test_healthy_data_returns_empty():
    """全部健康评论（高分+正面+无负面标签+无日期上下文）不触发任何规则。"""
    reviews = make_batch(20, rating=5, sentiment="推荐", tags={})
    assert detect_anomalies(reviews) == []


def test_results_sorted_by_severity_desc():
    """多信号时按严重度降序（高>中>低）排列。"""
    reviews = []
    # 10 条质量差 -> 质量隐患集中[高]
    reviews += [
        make_review(f"q{i}", tags={"质量_材质": "差"})
        for i in range(10)
    ]
    # 5 条不会复购 -> 复购流失预警[低]（5%）
    reviews += [
        make_review(f"c{i}", tags={"复购_复购意愿": "不会"})
        for i in range(5)
    ]
    # 其余健康评论补足 100
    reviews += make_batch(85, rating=5, sentiment="推荐", tags={})

    signals = detect_anomalies(reviews)
    order = {"高": 0, "中": 1, "低": 2}
    ranks = [order[s.severity] for s in signals]
    assert ranks == sorted(ranks)
    assert find(signals, "质量隐患集中").severity == "高"
    assert find(signals, "复购流失预警").severity == "低"


# ==================== 规则 1: 高分低情隐性流失 ====================


def _rule1_batch(matched_count, matched_kwargs):
    reviews = [make_review(f"m{i}", **matched_kwargs) for i in range(matched_count)]
    reviews += make_batch(100 - matched_count, rating=5, sentiment="推荐", tags={})
    return reviews


def test_rule1_sentiment_gap_high():
    """占比>=10% -> 高。10/100 高分负面。"""
    reviews = _rule1_batch(10, {"rating": 4, "sentiment": "不推荐"})
    sig = find(detect_anomalies(reviews), "高分低情隐性流失")
    assert sig is not None
    assert sig.severity == "高"
    assert sig.affected_count == 10
    assert sig.affected_pct == 10.0


def test_rule1_sentiment_gap_mid():
    """占比 5%-10% -> 中。6/100。"""
    reviews = _rule1_batch(6, {"rating": 5, "sentiment": "强烈不推荐"})
    sig = find(detect_anomalies(reviews), "高分低情隐性流失")
    assert sig is not None
    assert sig.severity == "中"


def test_rule1_sentiment_gap_low():
    """占比 2%-5% -> 低。3/100。"""
    reviews = _rule1_batch(3, {"rating": 4, "sentiment": "中立"})
    sig = find(detect_anomalies(reviews), "高分低情隐性流失")
    assert sig is not None
    assert sig.severity == "低"


def test_rule1_below_threshold_no_signal():
    """占比<2% 不触发。1/100。"""
    reviews = _rule1_batch(1, {"rating": 4, "sentiment": "不推荐"})
    assert find(detect_anomalies(reviews), "高分低情隐性流失") is None


def test_rule1_negative_overall_tag_counts():
    """rating>=4 但 tags.情感_总体评价 为负面同样命中。"""
    reviews = _rule1_batch(5, {"rating": 5, "sentiment": "推荐",
                               "tags": {"情感_总体评价": "不推荐"}})
    sig = find(detect_anomalies(reviews), "高分低情隐性流失")
    assert sig is not None
    assert sig.affected_count == 5


def test_rule1_low_rating_negative_not_matched():
    """低分（<4）负面评论不属于「隐性流失」，不命中规则 1。"""
    reviews = _rule1_batch(10, {"rating": 1, "sentiment": "不推荐"})
    assert find(detect_anomalies(reviews), "高分低情隐性流失") is None


# ==================== 规则 2: 质量隐患集中 ====================


def _rule2_batch(n, tag):
    reviews = [make_review(f"q{i}", tags={tag[0]: tag[1]}) for i in range(n)]
    reviews += make_batch(100 - n, rating=5, sentiment="推荐", tags={})
    return reviews


def test_rule2_quality_high():
    """N>=10 -> 高（即使占比仅 10%）。"""
    sig = find(detect_anomalies(_rule2_batch(10, ("质量_材质", "差"))),
               "质量隐患集中")
    assert sig is not None
    assert sig.severity == "高"
    assert sig.affected_count == 10
    assert "质量_材质:差=10条" in sig.detail


def test_rule2_quality_mid():
    """占比 8%-15% 且 N<10 -> 中。9/100=9%。"""
    sig = find(detect_anomalies(_rule2_batch(9, ("质量_做工", "粗糙"))),
               "质量隐患集中")
    assert sig is not None
    assert sig.severity == "中"


def test_rule2_quality_low():
    """占比 3%-8% -> 低。5/100=5%。"""
    sig = find(detect_anomalies(_rule2_batch(5, ("质量_耐用性", "易坏"))),
               "质量隐患集中")
    assert sig is not None
    assert sig.severity == "低"


def test_rule2_below_threshold_no_signal():
    """占比<3% 不触发。2/100=2%。"""
    assert find(detect_anomalies(_rule2_batch(2, ("质量_材质", "差"))),
                "质量隐患集中") is None


def test_rule2_dedup_and_subdim_counts():
    """同一评论命中多个质量子维度只计 1 条，子维度计数各自累加。"""
    reviews = [
        make_review("q0", tags={"质量_材质": "差", "质量_做工": "粗糙",
                                "质量_耐用性": "易坏"}),
    ] + [
        make_review(f"q{i}", tags={"质量_材质": "差"}) for i in range(1, 9)
    ]
    reviews += make_batch(91, rating=5, sentiment="推荐", tags={})
    sig = find(detect_anomalies(reviews), "质量隐患集中")
    assert sig is not None
    assert sig.affected_count == 9  # 去重后 9 条，非 11
    assert sig.severity == "中"  # 9% 且 N=9<10
    assert "质量_材质:差=9条" in sig.detail
    assert "质量_做工:粗糙=1条" in sig.detail
    assert "质量_耐用性:易坏=1条" in sig.detail


# ==================== 规则 3: 退货售后集中爆发 ====================


def _rule3_batch(n, tag):
    reviews = [make_review(f"s{i}", tags={tag[0]: tag[1]}) for i in range(n)]
    reviews += make_batch(100 - n, rating=5, sentiment="推荐", tags={})
    return reviews


def test_rule3_return_difficulty_high():
    """退换货困难占比>=8% 直接判高（即使命中集合整体仅 8%<12%）。"""
    sig = find(detect_anomalies(_rule3_batch(8, ("服务_退换货", "困难"))),
               "退货售后集中爆发")
    assert sig is not None
    assert sig.severity == "高"
    assert "退换货困难: 8条(8.0%)" in sig.detail


def test_rule3_collection_mid():
    """命中集合占比>=12%（退换货困难<8%）-> 中。12/100 客服迟缓。"""
    sig = find(detect_anomalies(_rule3_batch(12, ("服务_客服响应", "迟缓"))),
               "退货售后集中爆发")
    assert sig is not None
    assert sig.severity == "中"


def test_rule3_collection_low():
    """命中集合占比 5%-12% -> 低。5/100 包装破损。"""
    sig = find(detect_anomalies(_rule3_batch(5, ("服务_包装质量", "破损"))),
               "退货售后集中爆发")
    assert sig is not None
    assert sig.severity == "低"


def test_rule3_below_threshold_no_signal():
    """占比<5% 不触发。4/100 无保修。"""
    assert find(detect_anomalies(_rule3_batch(4, ("服务_保修", "无保修"))),
                "退货售后集中爆发") is None


def test_rule3_dedup():
    """同一评论同时命中退换货困难+客服迟缓只计 1 条命中、退换货计 1。"""
    reviews = [make_review("s0", tags={"服务_退换货": "困难",
                                       "服务_客服响应": "迟缓"})]
    reviews += make_batch(99, rating=5, sentiment="推荐", tags={})
    sig = find(detect_anomalies(reviews), "退货售后集中爆发")
    assert sig is None  # 去重后 1 条=1%，低于阈值


# ==================== 规则 4a: 负面突增（有日期） ====================


def _dated(neg_count, total, age_days):
    """构造一组带日期评论：前 neg_count 条负面（低分），其余正面。"""
    reviews = []
    for i in range(total):
        if i < neg_count:
            reviews.append(make_review(
                f"d{age_days}_{i}", rating=1, sentiment="不推荐",
                date=(datetime.now() - timedelta(days=age_days)).strftime("%Y-%m-%d")))
        else:
            reviews.append(make_review(
                f"d{age_days}_{i}", rating=5, sentiment="推荐",
                date=(datetime.now() - timedelta(days=age_days)).strftime("%Y-%m-%d")))
    return reviews


def _surge(recent, baseline):
    ctx = {"has_review_date": True}
    return find(detect_anomalies(recent + baseline, context=ctx), "负面突增")


def test_rule4a_negative_surge_high():
    """近期 50% vs 基线 10%，差值 40pp -> 高。"""
    sig = _surge(_dated(5, 10, 5), _dated(2, 20, 60))
    assert sig is not None
    assert sig.severity == "高"
    assert sig.affected_count == 5
    assert "差值 +40.0pp" in sig.detail


def test_rule4a_negative_surge_mid():
    """近期 20% vs 基线 5%，差值 15pp -> 中。"""
    sig = _surge(_dated(2, 10, 5), _dated(1, 20, 60))
    assert sig is not None
    assert sig.severity == "中"


def test_rule4a_negative_surge_low():
    """近期 20% vs 基线 12%，差值 8pp -> 低（8pp 是触发下限）。"""
    sig = _surge(_dated(2, 10, 5), _dated(3, 25, 60))
    assert sig is not None
    assert sig.severity == "低"


def test_rule4a_diff_below_threshold_no_signal():
    """差值<8pp 不触发。近期 20% vs 基线 15%。"""
    assert _surge(_dated(2, 10, 5), _dated(3, 20, 60)) is None


def test_rule4a_insufficient_recent_sample_no_signal():
    """近 30 天样本<10 不触发（即使近期负面率 100%）。"""
    assert _surge(_dated(4, 4, 5), _dated(0, 20, 60)) is None


# ==================== 规则 4b: 负面率绝对值（无日期降级） ====================


def test_rule4b_absolute_negative_rate_high():
    """无日期上下文时降级为绝对值判断：负面率>=30% -> 高。"""
    reviews = _dated(35, 100, 5)
    for r in reviews:
        r["date"] = ""  # 清掉日期，走降级路径
    sig = find(detect_anomalies(reviews), "负面突增")
    assert sig is not None
    assert sig.severity == "高"
    assert sig.affected_pct == 35.0


def test_rule4b_below_30pct_no_signal():
    """负面率<30% 不触发。"""
    reviews = _dated(29, 100, 5)
    for r in reviews:
        r["date"] = ""
    assert find(detect_anomalies(reviews), "负面突增") is None


# ==================== 规则 5: 复购流失预警 ====================


def _rule5_batch(n):
    reviews = [make_review(f"c{i}", tags={"复购_复购意愿": "不会"})
               for i in range(n)]
    reviews += make_batch(100 - n, rating=5, sentiment="推荐", tags={})
    return reviews


def test_rule5_repurchase_churn_high():
    """不会复购占比>=15% -> 高。16/100。"""
    sig = find(detect_anomalies(_rule5_batch(16)), "复购流失预警")
    assert sig is not None
    assert sig.severity == "高"
    assert sig.affected_count == 16


def test_rule5_repurchase_churn_mid():
    """占比 8%-15% -> 中。10/100。"""
    sig = find(detect_anomalies(_rule5_batch(10)), "复购流失预警")
    assert sig is not None
    assert sig.severity == "中"


def test_rule5_repurchase_churn_low():
    """占比 3%-8% -> 低。5/100。"""
    sig = find(detect_anomalies(_rule5_batch(5)), "复购流失预警")
    assert sig is not None
    assert sig.severity == "低"


def test_rule5_below_threshold_no_signal():
    """占比<3% 不触发。2/100。"""
    assert find(detect_anomalies(_rule5_batch(2)), "复购流失预警") is None


def test_rule5_price_perception_upgrades_severity():
    """叠加体验_价格感知==偏贵>=10% 自动升一级：低->中。"""
    stats = {"dimensional_stats": {"体验_价格感知": {"偏贵": 3, "合理": 7}}}
    sig = find(detect_anomalies(_rule5_batch(5), stats=stats), "复购流失预警")
    assert sig is not None
    assert sig.severity == "中"
    assert "严重度升级" in sig.detail


def test_rule5_price_perception_upgrades_mid_to_high():
    """中 + 偏贵叠加 -> 升为高。"""
    stats = {"dimensional_stats": {"体验_价格感知": {"偏贵": 5, "合理": 5}}}
    sig = find(detect_anomalies(_rule5_batch(10), stats=stats), "复购流失预警")
    assert sig is not None
    assert sig.severity == "高"


def test_rule5_price_perception_below_upgrade_threshold():
    """偏贵占比<10% 不升级。10/100 本为中，偏贵 5% -> 维持中。"""
    stats = {"dimensional_stats": {"体验_价格感知": {"偏贵": 1, "合理": 19}}}
    sig = find(detect_anomalies(_rule5_batch(10), stats=stats), "复购流失预警")
    assert sig is not None
    assert sig.severity == "中"

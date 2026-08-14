#!/usr/bin/env python3
"""
从已打标CSV直接生成报告的脚本（V2.1 版）
跳过 Phase 1 打标阶段，复用已有 22 维标签，直接执行画像 → 统计 → 异常检测 → 15章洞察报告。

适用场景：评论已打标（如 `评论采集及打标数据_{ASIN}.csv` 或飞书打标表格导出），
想用新版报告管线（V2.1：15章 + 异常信号卡）重新出报告，不再花 LLM 成本重新打标。

用法:
    python3 tools/generate_from_tagged.py <已打标CSV路径> [--creator 署名] [--output-dir 输出目录]

CSV 列要求（兼容新旧两种列名）:
    原始列:  asin/ASIN, rating/星级, review_title/标题, review_content/review_body/内容
    打标列:  人群_性别 等 22 维标签列 + 情感_总体评价 + info_score(可选)
"""

import os
import sys
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, generate_insights
from src.anomaly_detector import detect_anomalies

# 22 维标签列（V2.1 口径）
TAG_COLUMNS = [
    '人群_性别', '人群_年龄段', '人群_职业', '人群_购买角色',
    '场景_使用场景', '功能_满意度', '功能_具体功能',
    '质量_材质', '质量_做工', '质量_耐用性',
    '服务_发货速度', '服务_包装质量', '服务_客服响应', '服务_退换货', '服务_保修',
    '体验_舒适度', '体验_易用性', '体验_外观设计', '体验_价格感知',
    '竞品_竞品对比', '市场_竞品对比',  # 新旧列名都认
    '复购_复购意愿', '情感_总体评价',
]

# 原始评论列的新旧列名映射（先命中先用）
BODY_KEYS = ['review_content', 'review_body', '内容', '评论内容']
RATING_KEYS = ['rating', '星级', '评分']
TITLE_KEYS = ['review_title', '标题']
DATE_KEYS = ['review_date', '评论时间', 'date', '时间']


def _pick(row, keys, default=''):
    """按候选列名顺序取第一个非空值"""
    for k in keys:
        v = row.get(k, None)
        if v is not None and pd.notna(v) and str(v).strip() != '':
            return v
    return default


def load_tagged_csv(csv_path: str):
    """加载已打标CSV，重建 V2.1 tagged_reviews 结构"""
    print(f"📄 加载已打标CSV: {csv_path}")

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"   ✓ 成功加载 {len(df)} 行")

    has_tags = '人群_性别' in df.columns or '情感_总体评价' in df.columns
    if not has_tags:
        raise ValueError(
            "CSV 中未找到打标列（人群_性别 / 情感_总体评价 等），"
            "请确认输入是已打标数据；未打标的原始评论请走 main.py 完整流程"
        )

    reviews = []
    for _, row in df.iterrows():
        body = str(_pick(row, BODY_KEYS, '')).strip()
        if not body:
            continue  # 无正文的行跳过

        tags = {}
        for col in TAG_COLUMNS:
            if col in df.columns:
                v = row.get(col, '')
                if pd.notna(v) and str(v).strip() != '':
                    tags[col] = str(v).strip()

        rating = _pick(row, RATING_KEYS, 0)
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            rating = 0.0

        info_score = _pick(row, ['info_score'], 0)
        try:
            info_score = int(float(info_score))
        except (TypeError, ValueError):
            info_score = 0

        reviews.append({
            'review_id': str(_pick(row, ['review_id'], len(reviews) + 1)),
            'title': str(_pick(row, TITLE_KEYS, '')),
            'body': body,
            'rating': rating,
            'date': str(_pick(row, DATE_KEYS, '')),
            'sentiment': str(_pick(row, ['情感_总体评价'], '中立') or '中立'),
            'info_score': info_score,
            'tags': tags,
            '_original_data': {k: row.get(k, '') for k in df.columns},
        })

    print(f"   ✓ 重建 tagged_reviews: {len(reviews)} 条（含 22 维标签）")
    return reviews, df


def extract_asin(df: pd.DataFrame, csv_path: str) -> str:
    """提取 ASIN：优先文件名，其次 asin 列众数"""
    match = re.search(r'B[A-Z0-9]{9}', csv_path.upper())
    if match:
        return match.group(0)
    for col in ('asin', 'ASIN'):
        if col in df.columns and not df[col].dropna().empty:
            return str(df[col].value_counts().idxmax())
    return "UNKNOWN"


def main():
    print("=" * 70)
    print("🚀 从已打标CSV直接生成报告 V2.1（15章 + 异常信号卡）")
    print("=" * 70)

    if len(sys.argv) < 2:
        print("用法: python3 tools/generate_from_tagged.py <已打标CSV路径> [--creator 署名] [--output-dir 输出目录]")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)

    creator = "AI Assistant"
    output_dir = None
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == "--creator" and i + 1 < len(sys.argv):
            creator = sys.argv[i + 1]
        elif sys.argv[i] == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]

    config.OUTPUT_DIR = Path(output_dir) if output_dir else Path(csv_path).parent
    config.HTML_CREATOR_NAME = creator
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    reviews, df = load_tagged_csv(csv_path)
    if not reviews:
        print("❌ 未重建出有效打标数据")
        sys.exit(1)

    asin = extract_asin(df, csv_path)
    print(f"📦 产品ASIN: {asin}")
    print(f"📁 输出目录: {config.OUTPUT_DIR}")

    # Phase 2: 用户画像识别
    print(f"\n👥 [Phase 2/3] 用户画像识别中...")
    personas, golden_samples = analyze_user_personas(reviews)
    print(f"✅ [Phase 2/3] 完成！识别到 {len(personas)} 个画像，{len(golden_samples)} 条黄金样本")

    # Phase 3: 统计 + 异常检测 + 15章洞察报告（与 main.py V2.1 调用链一致）
    print(f"\n📝 [Phase 3/3] AI深度战略洞察报告生成中...")
    stats = calculate_stats_summary(reviews)

    anomaly_context = {
        "has_review_date": any(
            r.get("date") and str(r.get("date")).strip() not in ("", "nan", "None", "null")
            for r in reviews
        )
    }
    anomaly_signals = detect_anomalies(reviews, stats, anomaly_context)
    if anomaly_signals:
        print(f"   ⚠️  检测到 {len(anomaly_signals)} 条异常信号: "
              f"{', '.join(f'{s.signal_type}[{s.severity}]' for s in anomaly_signals)}")
    else:
        print("   ✅ 未检测到异常信号")

    insights_md = generate_insights(
        stats=stats,
        personas=personas,
        golden_samples=golden_samples,
        asin=asin,
        anomaly_signals=anomaly_signals,
    )

    report_path = config.OUTPUT_DIR / f"分析洞察报告_{asin}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(insights_md or "")

    if insights_md:
        print(f"✅ [Phase 3/3] 洞察报告已生成！字数约 {len(insights_md):,} 字")
        print(f"📄 报告路径: {report_path}")
    else:
        print("⚠️ 报告生成为空，请检查 CLI 引擎配置")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
快速重放脚本：从已打标的 CSV 跳过 Phase 1，直接执行 Phase 2-5
用法：python3 replay_phase2to5.py <tagged_csv> [--template TEMPLATE]
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import pandas as pd

# 项目根目录
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.config import config
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, generate_insights
from src.report_generator import generate_html_report
from src.output_manager import generate_outputs


def load_tagged_csv(csv_path: str) -> list:
    """从已打标 CSV 加载评论数据"""
    df = pd.read_csv(csv_path)
    reviews = []
    for _, row in df.iterrows():
        tags = {}
        tag_columns = [c for c in df.columns if any(
            prefix in c for prefix in
            ['人群_', '场景_', '功能_', '质量_', '服务_', '体验_', '竞品_', '复购_']
        )]
        for col in tag_columns:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                tags[col] = str(val).strip()

        sentiment = str(row.get('情感_总体评价', '')).strip() if pd.notna(row.get('情感_总体评价')) else ''

        review = {
            'body': str(row.get('Content', row.get('content', ''))).strip(),
            'rating': int(row.get('Rating', row.get('rating', 0))) if pd.notna(row.get('Rating', row.get('rating'))) else 0,
            'sentiment': sentiment,
            'tags': tags,
            'date': str(row.get('Date', row.get('date', ''))).strip() if pd.notna(row.get('Date', row.get('date'))) else '',
            'author': str(row.get('Author', row.get('author', ''))).strip() if pd.notna(row.get('Author', row.get('author'))) else '',
        }
        reviews.append(review)
    return reviews


def extract_asin_from_path(csv_path: str) -> str:
    """从文件名或路径中提取 ASIN"""
    name = Path(csv_path).stem
    # 尝试从文件名中提取 ASIN (格式通常为 xxx_B0XXXXX)
    import re
    match = re.search(r'(B0[A-Z0-9]{7,})', name)
    if match:
        return match.group(1)
    return 'UNKNOWN'


def main():
    parser = argparse.ArgumentParser(description='重放 Phase 2-5（跳过打标）')
    parser.add_argument('csv_file', help='已打标的 CSV 文件路径')
    parser.add_argument('--template', default='stripe-executive', help='HTML 模板名称')
    parser.add_argument('--creator', default='Buluu@新西楼', help='署名')
    parser.add_argument('--output-dir', default=None, help='输出目录')
    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)

    asin = extract_asin_from_path(str(csv_path))
    print(f"📋 ASIN: {asin}, 模板: {args.template}")

    # 配置（统一 CLI 本地模式）
    config.HTML_CREATOR_NAME = args.creator
    if args.output_dir:
        config.OUTPUT_DIR = Path(args.output_dir)
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 加载已打标数据
    print(f"\n📄 加载已打标数据: {csv_path.name}")
    tagged_reviews = load_tagged_csv(str(csv_path))
    print(f"   ✅ 加载 {len(tagged_reviews)} 条已打标评论")

    # Phase 2: 用户画像
    print(f"\n👥 [Phase 2/4] 用户画像识别...")
    personas, golden_samples = analyze_user_personas(tagged_reviews)
    print(f"   ✅ {len(personas)} 个画像, {len(golden_samples)} 条黄金样本")

    # Phase 3: 洞察报告
    print(f"\n📝 [Phase 3/4] AI 深度洞察报告生成中...")
    stats = calculate_stats_summary(tagged_reviews)
    insights_md = generate_insights(
        stats=stats, personas=personas, golden_samples=golden_samples, asin=asin
    )
    if insights_md:
        print(f"   ✅ 报告已生成 ({len(insights_md):,} 字)")
    else:
        print(f"   ⚠️ 报告生成失败")
        insights_md = ""

    # 保存 MD
    md_path = config.get_md_path(asin)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(insights_md)

    # Phase 4: HTML 看板 (V1 report_generator)
    print(f"\n🎨 [Phase 4a] V1 HTML 看板生成...")
    summary = {
        "total": len(tagged_reviews),
        "tagged": stats["tagged"],
        "persona_count": len(personas),
        "avg_rating": stats.get("avg_rating", 0),
        "sentiment": stats.get("sentiment", {}),
        "top_tags": stats.get("top_tags", {})
    }
    html_path = generate_html_report(
        asin=asin, summary=summary, personas=personas,
        sentiment_distribution=stats["sentiment"],
        tag_statistics=stats["top_tags"],
        golden_samples=golden_samples,
        insights_md=insights_md,
        creator_name=config.HTML_CREATOR_NAME
    )
    print(f"   ✅ V1 看板: {html_path.name if html_path else '失败'}")

    # Phase 5: OutputManager (V2 模板看板)
    print(f"\n📦 [Phase 4b] V2 模板看板生成 ({args.template})...")
    analysis_data = {
        "asin": asin, "product_name": asin,
        "total_reviews": len(tagged_reviews),
        "avg_rating": stats.get("avg_rating", 0),
        "summary": summary,
        "sentiment": stats.get("sentiment", {}),
        "sentiment_distribution": stats.get("sentiment", {}),
        "tag_statistics": stats.get("top_tags", {}),
        "top_tags": stats.get("top_tags", {}),
        "personas": [{"name": p.get("name",""), "count": p.get("count",0), "tags": p.get("tags",{})} for p in personas],
        "golden_samples": golden_samples,
        "insights_md": insights_md,
        "statistics": stats,
    }
    output_config = {
        "template_name": args.template,
        "sync_feishu": False,
        "output_dir": str(config.OUTPUT_DIR),
        "asin": asin,
        "creator": config.HTML_CREATOR_NAME,
    }
    output_results = generate_outputs(analysis_data, output_config)

    v2_html = output_results.get("html_path", "")
    print(f"   ✅ V2 看板: {v2_html}")

    print("\n" + "✨" * 30)
    print("🎉 重放完成！")
    print(f"  - 洞察报告: {md_path.name}")
    print(f"  - V1 看板: {html_path.name if html_path else 'N/A'}")
    print(f"  - V2 看板: {Path(v2_html).name if v2_html else 'N/A'}")
    print("✨" * 30)


if __name__ == "__main__":
    main()

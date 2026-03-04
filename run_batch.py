#!/usr/bin/env python3
"""
批量分析脚本 - 非交互式版本
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 导入所有核心模块
from src.data_loader import load_reviews_from_file
from src.review_analyzer import analyze_all
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, generate_insights
from src.report_generator import generate_html_report
from src.config import config


def extract_asin_from_file(file_path: str) -> str:
    """从文件名提取 ASIN"""
    filename = Path(file_path).stem
    import re
    asin_pattern = r'[A-Z0-9]{10}'
    matches = re.findall(asin_pattern, filename.upper())
    return matches[0] if matches else filename.upper()[:10]


def save_tagged_reviews_to_csv(tagged_reviews: list, asin: str) -> Path:
    """将打标后的评论数据保存为 CSV 文件"""
    flattened_reviews = []
    for review in tagged_reviews:
        original_data = review.get("_original_data", {})
        flat_row = dict(original_data)
        tags = review.get("tags", {})
        for tag_key, tag_value in tags.items():
            if tag_key != "情感_总体评价":
                flat_row[tag_key] = tag_value
        flat_row["情感_总体评价"] = tags.get("情感_总体评价", "")
        flat_row["评论价值打分"] = review.get("info_score", 0)
        flat_row["打标时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        flattened_reviews.append(flat_row)

    df = pd.DataFrame(flattened_reviews)
    csv_path = config.get_csv_path(asin)
    df.to_csv(csv_path, index=False, encoding=config.CSV_ENCODING)
    return csv_path


def main():
    """主函数 - 非交互式批量处理"""
    parser = argparse.ArgumentParser(description="Amazon Review Analyzer - Batch Mode")
    parser.add_argument("input_file", help="输入文件路径")
    parser.add_argument("--max-reviews", type=int, default=None, help="最大处理评论数")
    parser.add_argument("--batch-size", type=int, default=30, help="每批处理数量")
    parser.add_argument("--mode", choices=["cli", "gemini"], default="cli", help="分析模式")
    parser.add_argument("--creator", default="AI分析", help="报告署名")
    args = parser.parse_args()

    print("🚀 开始批量分析...")

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ 错误：找不到文件: {input_path}")
        sys.exit(1)

    asin = extract_asin_from_file(args.input_file)
    print(f"📦 ASIN: {asin}")

    # 设置模式
    config.INSIGHTS_PROVIDER = args.mode
    config.HTML_GENERATION_SOURCE = "local" if args.mode == "cli" else "gemini"
    config.HTML_CREATOR_NAME = args.creator

    try:
        print("📂 加载评论数据...")
        reviews, original_df = load_reviews_from_file(args.input_file)
        print(f"✅ 加载成功: {len(reviews)} 条评论")

        # 设置最大处理数量
        if args.max_reviews:
            config.MAX_REVIEWS = min(args.max_reviews, len(reviews))
            print(f"⚙️  最大处理数: {config.MAX_REVIEWS}")
        else:
            config.MAX_REVIEWS = len(reviews)

        if len(reviews) > config.MAX_REVIEWS:
            reviews = reviews[:config.MAX_REVIEWS]

        # ========== 执行阶段 ==========

        # 🟢 打标分析
        print(f"\n🚀 [Phase 1] 正在进行 AI 深度打标分析...")
        print(f"   处理模式: {args.mode.upper()}")
        print(f"   批次大小: {args.batch_size}")
        tagged_reviews = analyze_all(reviews, batch_size=args.batch_size)
        print(f"   ✅ 打标完成: {len(tagged_reviews)} 条")

        # 🟡 画像识别
        print(f"\n👥 [Phase 2] 正在识别用户画像...")
        personas, golden_samples = analyze_user_personas(tagged_reviews)

        if not personas:
            print("   ⚠️  画像警报：样本分布过于稀疏，将产出全量用户分析模板")
        else:
            print(f"   ✅ 画像成功：捕获到 {len(personas)} 组典型用户群体")

        # 🔵 洞察生成
        print(f"\n📝 [Phase 3] 正在生成深度战略洞察报告...")
        stats = calculate_stats_summary(tagged_reviews)
        insights_md = generate_insights(
            stats=stats,
            personas=personas,
            golden_samples=golden_samples,
            asin=asin
        )

        md_path = config.get_md_path(asin)
        if insights_md:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(insights_md)
            print(f"   ✅ Markdown 报告已保存: {md_path}")

        csv_path = save_tagged_reviews_to_csv(tagged_reviews, asin)
        print(f"   ✅ CSV 数据已保存: {csv_path}")

        # 🎨 看板渲染
        print(f"\n🎨 [Phase 4] 正在渲染可视化看板...")
        summary = {
            "total_reviews": len(tagged_reviews),
            "tagged_reviews": stats["tagged"],
            "persona_count": len(personas),
            "avg_rating": round(sum(r.get("rating", 0) for r in tagged_reviews) / len(tagged_reviews), 2) if tagged_reviews else 0
        }

        html_path = generate_html_report(
            asin=asin,
            summary=summary,
            personas=personas,
            sentiment_distribution=stats["sentiment"],
            tag_statistics=stats["top_tags"],
            golden_samples=golden_samples,
            insights_md=insights_md,
            creator_name=config.HTML_CREATOR_NAME
        )
        print(f"   ✅ HTML 看板已保存: {html_path}")

        # ========== 完成 ==========
        print("\n" + "✨" * 30)
        print("🎉 分析完成！生成的文件：")
        print(f"  📄 文字报告: {md_path.name}")
        print(f"  📊 结构数据: {csv_path.name}")
        print(f"  🎨 可视化看板: {html_path.name}")
        print(f"  📁 输出目录: {config.OUTPUT_DIR}")
        print("✨" * 30 + "\n")

    except Exception as e:
        print(f"\n❌ 执行遇到严重故障: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

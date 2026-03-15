#!/usr/bin/env python3
"""
从已打标的CSV文件重新生成洞察报告（跳过打标和可视化步骤）
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 使用相对路径以增强兼容性
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, generate_insights
from src.config import config
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def load_tagged_csv(csv_path: str):
    """加载已打标的CSV文件"""
    df = pd.read_csv(csv_path)

    # 查找标签列（以_开头的列）
    tag_columns = [col for col in df.columns if '_' in col and not col.startswith('_')]

    # 转换为打标评论格式
    tagged_reviews = []
    for _, row in df.iterrows():
        tags = {}
        for col in tag_columns:
            if col in row and pd.notna(row[col]):
                tags[col] = str(row[col])

        review = {
            "_original_data": row.to_dict(),
            "tags": tags,
            "sentiment": tags.get("情感_总体评价", ""),
            "rating": row.get("Rating", 0),
            "info_score": row.get("评论价值打分", 0)
        }
        tagged_reviews.append(review)

    return tagged_reviews, df

def main():
    if len(sys.argv) < 2:
        print("用法: python3 regenerate_insights.py <已打标CSV文件路径> [--creator 署名] [--mode 1|2|3]")
        sys.exit(1)

    csv_path = sys.argv[1]
    creator = "AI Assistant"
    mode = "1"

    # 解析可选参数
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--creator" and i + 1 < len(sys.argv):
            creator = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    print("🔄 从已打标CSV文件重新生成洞察报告")
    print("=" * 60)
    print(f"📁 输入文件: {csv_path}")
    print(f"✍️  报告署名: {creator}")
    print("=" * 60)
    print()

    # 设置输出目录为CSV文件所在目录
    csv_file_path = Path(csv_path)
    config.OUTPUT_DIR = csv_file_path.parent
    config.HTML_CREATOR_NAME = creator

    # 设置API Key
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        config.GEMINI_API_KEY = gemini_key

    # 设置模式
    if mode == "1":
        config.INSIGHTS_PROVIDER = "gemini"
        config.GEMINI_MODEL = "gemini-3-flash-preview"
        print("🤖 使用 Gemini 增强模式生成报告")
    elif mode == "2":
        config.INSIGHTS_PROVIDER = "cli"
        print("🤖 使用 Claude CLI 模式生成报告")
    else:
        config.INSIGHTS_PROVIDER = "cli"
        print("🤖 使用 Claude CLI 本地模式生成报告")

    # 加载已打标数据
    print(f"\n📄 正在加载已打标数据...")
    tagged_reviews, df = load_tagged_csv(csv_path)
    print(f"✅ 成功加载 {len(tagged_reviews)} 条已打标评论")

    # 提取ASIN
    asin = "UNKNOWN"
    if "Asin" in df.columns:
        asin = df["Asin"].iloc[0]
    else:
        # 从文件名提取
        import re
        filename = csv_file_path.stem
        asin_pattern = r'[A-Z0-9]{10}'
        matches = re.findall(asin_pattern, filename.upper())
        if matches:
            asin = matches[0]

    # Phase 1: 用户画像识别
    print(f"\n👥 [Phase 1/2] 用户画像识别中...")
    print(f"   - 正在分析 {len(tagged_reviews)} 条打标评论...")
    personas, golden_samples = analyze_user_personas(tagged_reviews)
    print(f"✅ [Phase 1/2] 用户画像识别完成！识别到 {len(personas)} 个画像，{len(golden_samples)} 条黄金样本")

    # Phase 2: 生成洞察报告
    print(f"\n📝 [Phase 2/2] AI深度战略洞察报告生成中...")
    print(f"   - 正在生成 {len(personas)} 个用户画像分析...")
    if config.INSIGHTS_PROVIDER == "gemini":
        print(f"   - 使用引擎: Gemini API ({config.GEMINI_MODEL})")
    else:
        print(f"   - 使用引擎: Claude Code CLI")

    from src.insights_generator import generate_insights_with_metadata
    
    result = generate_insights_with_metadata(
        tagged_reviews=tagged_reviews,
        personas=personas,
        golden_samples=golden_samples,
        asin=asin
    )
    
    insights_md = result.get('report', '')

    if insights_md:
        print(f"✅ [Phase 2/2] 洞察报告已生成！字数约 {len(insights_md):,} 字")

        # 保存 Markdown
        md_path = config.get_md_path(asin)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(insights_md)

        print(f"\n✨ 洞察报告已保存到: {md_path}")
    else:
        print(f"⚠️ 洞察报告生成失败")
        sys.exit(1)

if __name__ == "__main__":
    main()

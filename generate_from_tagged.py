#!/usr/bin/env python3
"""
从已打标CSV直接生成报告的脚本
跳过Phase 1打标阶段，直接执行Phase 2-4
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import config
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import generate_insights_with_metadata, calculate_stats_summary
from src.report_generator import generate_html_report


def load_tagged_csv(csv_path: str):
    """加载已打标的CSV文件"""
    print(f"📄 加载已打标CSV: {csv_path}")

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"   ✓ 成功加载 {len(df)} 条打标评论")

    # 提取目标ASIN（从文件名）
    import re
    csv_name = sys.argv[1] if len(sys.argv) > 1 else ""
    match = re.search(r'B[A-Z0-9]{9}', csv_name)
    target_asin = match.group(0) if match else None

    # 如果找到了目标ASIN，只保留该ASIN的数据
    if target_asin and 'ASIN' in df.columns:
        df = df[df['ASIN'] == target_asin].copy()
        print(f"   ✓ 筛选目标ASIN {target_asin}: {len(df)} 条评论")

    # 转换为review格式 - 兼容calculate_stats_summary的格式
    reviews = []
    for idx, row in df.iterrows():
        # 检查是否有打标数据
        if '人群_性别' in df.columns:
            # 构建tags字典
            tags = {}
            tag_columns = ['人群_性别', '人群_年龄段', '人群_职业', '人群_购买角色',
                         '场景_使用场景', '功能_满意度', '功能_具体功能',
                         '质量_材质', '质量_做工', '质量_耐用性',
                         '服务_发货速度', '服务_包装质量', '服务_客服响应', '服务_退换货', '服务_保修',
                         '体验_舒适度', '体验_易用性', '体验_外观设计', '体验_价格感知',
                         '市场_竞品对比', '复购_复购意愿']

            for col in tag_columns:
                if col in df.columns:
                    value = row.get(col, '')
                    if pd.notna(value) and value != '':
                        tags[col] = value

            # 获取sentiment
            sentiment = row.get('情感_总体评价', '中立')
            if pd.isna(sentiment):
                sentiment = '中立'

            review = {
                'raw_review': row.get('内容', ''),
                'rating': row.get('星级', 0),
                'date': row.get('评论时间', ''),
                'title': row.get('标题', ''),
                'author': row.get('评论人', ''),
                'sentiment': sentiment,
                'tags': tags
            }
            reviews.append(review)

    print(f"   ✓ 有效打标数据: {len(reviews)} 条")
    return reviews, df


def extract_asin(df: pd.DataFrame) -> str:
    """从DataFrame中提取ASIN，优先使用文件名中的ASIN"""
    import re
    # 优先从文件名提取（因为文件名通常代表主要分析的产品）
    csv_name = sys.argv[1] if len(sys.argv) > 1 else ""
    # 匹配B开头的10位字母数字
    match = re.search(r'B[A-Z0-9]{9}', csv_name)
    if match:
        return match.group(0)

    # 如果文件名中没有，从CSV的ASIN列中提取最常见的
    if 'ASIN' in df.columns and not df['ASIN'].empty:
        # 返回最常见的ASIN
        return str(df['ASIN'].value_counts().idxmax())

    return "UNKNOWN"


def main():
    print("=" * 70)
    print("🚀 从已打标CSV直接生成报告 V1.0")
    print("=" * 70)

    # 参数检查
    if len(sys.argv) < 2:
        print("用法: python3 generate_from_tagged.py <已打标CSV路径> [--mode 1|2|3] [--creator 署名] [--output-dir 输出目录]")
        print("  mode: 1=Gemini增强, 2=混动, 3=CLI本地 (默认: 1)")
        print("  --output-dir: 指定输出目录，默认与CSV同目录")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)

    # 解析参数
    mode = "1"  # 默认Gemini增强模式
    creator = "AI Assistant"
    output_dir = None  # 默认输出到CSV同目录

    for i in range(2, len(sys.argv)):
        if sys.argv[i] == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
        elif sys.argv[i] == "--creator" and i + 1 < len(sys.argv):
            creator = sys.argv[i + 1]
        elif sys.argv[i] == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]

    # 初始化配置 - 直接修改全局config
    # 如果指定了输出目录，使用它；否则使用CSV所在目录
    if output_dir:
        config.OUTPUT_DIR = Path(output_dir)
    else:
        # 使用CSV所在目录作为输出目录
        config.OUTPUT_DIR = Path(csv_path).parent

    # 设置模式
    if mode == "1":
        # Gemini增强模式
        config.INSIGHTS_PROVIDER = "gemini"
        config.GEMINI_MODEL = "gemini-3-flash-preview"
        config.HTML_GENERATION_SOURCE = "gemini"
        config.HTML_GENERATION_MODEL = "gemini-3.1-pro-preview"
        config.HTML_CREATOR_NAME = creator
        print("💡 模式：Gemini 增强模式 (Flash报告 + 3.1 Pro看板)")
    elif mode == "2":
        # 混动模式
        config.INSIGHTS_PROVIDER = "cli"
        config.HTML_GENERATION_SOURCE = "gemini"
        config.HTML_GENERATION_MODEL = "gemini-3.1-pro-preview"
        config.HTML_CREATOR_NAME = creator
        print("💡 模式：混动模式 (CLI报告 + Gemini看板)")
    else:
        # CLI本地模式
        config.INSIGHTS_PROVIDER = "cli"
        config.HTML_GENERATION_SOURCE = "local"
        config.HTML_CREATOR_NAME = creator
        print("💡 模式：CLI 本地模式")

    # 检查API Key - 从环境变量读取（已通过 load_dotenv() 加载 .env）
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        config.GEMINI_API_KEY = gemini_key

    if config.HTML_GENERATION_SOURCE == "gemini":
        if not config.GEMINI_API_KEY:
            print("⚠️  警告：Gemini模式需要API Key，将回退到本地模式")
            config.HTML_GENERATION_SOURCE = "local"

    # 加载已打标CSV
    reviews, df = load_tagged_csv(csv_path)

    if not reviews:
        print("❌ 未找到有效打标数据")
        sys.exit(1)

    # 提取ASIN
    asin = extract_asin(df)
    print(f"📦 产品ASIN: {asin}")

    # 直接使用输出目录，不创建子目录
    project_dir = config.OUTPUT_DIR
    project_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 输出目录: {project_dir}")

    # Phase 2: 用户画像识别
    print(f"\n👥 [Phase 2/3] 用户画像识别中...")
    personas, golden_samples = analyze_user_personas(reviews)
    print(f"✅ [Phase 2/3] 用户画像识别完成！识别到 {len(personas)} 个画像")

    # Phase 3: 洞察报告生成
    print(f"\n📝 [Phase 3/3] AI深度战略洞察报告生成中...")
    print(f"   - 使用引擎: {config.INSIGHTS_PROVIDER.upper()}")

    if config.INSIGHTS_PROVIDER == "gemini":
        print(f"   - 正在调用 Gemini API 生成洞察...")
    else:
        print(f"   - 正在调用 Claude CLI 生成洞察...")

    result = generate_insights_with_metadata(
        tagged_reviews=reviews,
        personas=personas,
        golden_samples=golden_samples,
        asin=asin
    )

    # 写入报告文件
    report_path = project_dir / f"分析洞察报告_{asin}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(result['report'])

    print(f"✅ [Phase 3/3] 洞察报告已生成！字数约 {len(result['report'])} 字")

    # Phase 4: 可视化看板
    print(f"\n🎨 [Phase 4/3] 可视化看板渲染中...")
    print(f"   - 使用引擎: {config.HTML_GENERATION_SOURCE.upper()}")

    # 计算统计数据
    stats = calculate_stats_summary(reviews)

    html_path = generate_html_report(
        asin=asin,
        summary=stats,
        personas=personas,
        sentiment_distribution=stats.get("sentiment", {}),
        tag_statistics=stats.get("top_tags", {}),
        golden_samples=golden_samples,
        insights_md=result['report'],
        creator_name=creator
    )

    print(f"✅ [Phase 4/3] 可视化看板构建完成！文件: {html_path.name}")

    # 复制CSV到输出目录（如果源和目标不同）
    import shutil
    output_csv = project_dir / f"评论采集及打标数据_{asin}.csv"
    if str(csv_path) != str(output_csv):
        shutil.copy(csv_path, output_csv)
        print(f"📊 CSV已复制到: {output_csv}")
    else:
        print(f"📊 CSV已是目标文件，跳过复制")

    print("\n" + "=" * 70)
    print("🎉 报告生成完成！")
    print(f"  - 洞察报告: {report_path.name}")
    print(f"  - 可视化看板: {html_path.name}")
    print(f"  - 结构数据: {output_csv.name}")
    print("=" * 70)


if __name__ == "__main__":
    main()

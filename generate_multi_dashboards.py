#!/usr/bin/env python3
"""
生成3个版本的HTML可视化看板
1. 本地经典模板版本
2. Gemini Pro版本
3. Gemini Flash版本
"""

import os
import sys
import pandas as pd
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import config
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary
from src.report_generator import generate_html_report


def load_tagged_csv_and_report(csv_path: str, md_path: str):
    """加载已打标CSV和洞察报告"""
    print(f"📄 加载已打标CSV: {csv_path}")

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"   ✓ 成功加载 {len(df)} 条打标评论")

    # 读取洞察报告
    print(f"📝 加载洞察报告: {md_path}")
    with open(md_path, 'r', encoding='utf-8') as f:
        insights_md = f.read()
    print(f"   ✓ 成功加载洞察报告，字数约 {len(insights_md)} 字")

    # 转换为review格式
    reviews = []
    for idx, row in df.iterrows():
        if '人群_性别' in df.columns:
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
    return reviews, insights_md


def extract_asin(md_path: str) -> str:
    """从文件路径提取ASIN"""
    import re
    match = re.search(r'B[A-Z0-9]{9}', md_path)
    return match.group(0) if match else "UNKNOWN"


def main():
    print("=" * 70)
    print("🚀 多版本HTML看板生成器 V1.0")
    print("=" * 70)

    # 参数检查
    if len(sys.argv) < 3:
        print("用法: python3 generate_multi_dashboards.py <CSV路径> <MD路径> [输出目录]")
        sys.exit(1)

    csv_path = sys.argv[1]
    md_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    if not os.path.exists(csv_path):
        print(f"❌ CSV文件不存在: {csv_path}")
        sys.exit(1)

    if not os.path.exists(md_path):
        print(f"❌ MD文件不存在: {md_path}")
        sys.exit(1)

    # 设置输出目录
    if output_dir:
        config.OUTPUT_DIR = Path(output_dir)
    else:
        # 使用MD所在目录
        config.OUTPUT_DIR = Path(md_path).parent

    # 检查API Key
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    config.GEMINI_API_KEY = line.split('=', 1)[1].strip()
                    break

    # 加载数据
    reviews, insights_md = load_tagged_csv_and_report(csv_path, md_path)

    if not reviews:
        print("❌ 未找到有效打标数据")
        sys.exit(1)

    # 提取ASIN
    asin = extract_asin(md_path)
    print(f"📦 产品ASIN: {asin}")
    print(f"📁 输出目录: {config.OUTPUT_DIR}")

    # 用户画像识别
    print(f"\n👥 识别用户画像...")
    personas, golden_samples = analyze_user_personas(reviews)
    print(f"✅ 识别到 {len(personas)} 个画像")

    # 计算统计数据
    stats = calculate_stats_summary(reviews)

    # 生成3个版本的看板
    versions = [
        {
            "name": "本地经典模板",
            "file_suffix": "Local",
            "source": "local",
            "model": None,
            "description": "使用Jinja2模板渲染的本地版本"
        },
        {
            "name": "Gemini Pro增强版",
            "file_suffix": "GeminiPro",
            "source": "gemini",
            "model": "gemini-3.1-pro-preview",
            "description": "使用Gemini 3.1 Pro生成的高品质版本"
        },
        {
            "name": "Gemini Flash快速版",
            "file_suffix": "GeminiFlash",
            "source": "gemini",
            "model": "gemini-3-flash-preview",
            "description": "使用Gemini 3 Flash生成的快速版本"
        }
    ]

    results = []

    for i, version in enumerate(versions, 1):
        print(f"\n{'='*70}")
        print(f"🎨 [{i}/3] 生成{version['name']}")
        print(f"   {version['description']}")
        print(f"{'='*70}")

        # 配置生成模式
        config.HTML_GENERATION_SOURCE = version['source']
        config.HTML_GENERATION_MODEL = version['model']
        config.HTML_CREATOR_NAME = "AI Assistant"

        # 修改输出文件名
        original_get_html_path = config.get_html_path

        def custom_get_html_path(asin_param):
            """自定义路径，添加版本后缀"""
            project_dir = config._get_project_dir(asin_param)
            return project_dir / f"可视化洞察报告_{asin_param}_{version['file_suffix']}.html"

        config.get_html_path = custom_get_html_path

        try:
            html_path = generate_html_report(
                asin=asin,
                summary=stats,
                personas=personas,
                golden_samples=golden_samples,
                insights_md=insights_md,
                creator_name="AI Assistant"
            )

            # 复制到输出目录根目录
            import shutil
            final_path = config.OUTPUT_DIR / html_path.name
            if str(html_path) != str(final_path):
                shutil.copy(html_path, final_path)

            file_size = os.path.getsize(final_path) / 1024
            print(f"✅ 生成成功: {html_path.name} ({file_size:.1f} KB)")
            results.append({
                "version": version['name'],
                "file": html_path.name,
                "size": f"{file_size:.1f} KB",
                "status": "成功"
            })

        except Exception as e:
            print(f"❌ 生成失败: {e}")
            results.append({
                "version": version['name'],
                "file": "N/A",
                "size": "N/A",
                "status": f"失败: {e}"
            })

        finally:
            # 恢复原始函数
            config.get_html_path = original_get_html_path

    # 输出总结
    print(f"\n{'='*70}")
    print("📊 生成总结")
    print(f"{'='*70}")

    for result in results:
        status_icon = "✅" if result["status"] == "成功" else "❌"
        print(f"{status_icon} {result['version']}")
        print(f"   文件: {result['file']}")
        print(f"   大小: {result['size']}")
        print(f"   状态: {result['status']}")
        print()

    print(f"{'='*70}")
    print("🎉 所有版本生成完成！")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

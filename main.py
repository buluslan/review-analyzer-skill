#!/usr/bin/env python3
"""
Amazon 商品评论 AI 深度分析工具 - 主入口 V2.0 (Agent 原生版)
功能：支持交互式向导 + 全参数驱动 + Sorftime数据对接 + 多模板看板 + 飞书同步
"""

import sys
import argparse
import re
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 导入核心模块
from src.data_loader import load_reviews_from_file, download_if_url
from src.review_analyzer import analyze_all
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, generate_insights
from src.report_generator import generate_html_report
from src.config import config, mask_api_key

# V2.0 新模块
from src.data_fetchers import get_fetcher, list_fetchers
from src.output_manager import OutputManager
from src.prompts.manager import list_chapters


def print_intro():
    """打印工具详细说明"""
    print("""
🚀 多场景评论内容 AI 深度分析工具 V2.0 — Agent 原生版 Created By Buluu@新西楼
======================================================================
核心功能: 22维度智能标签 · 13章深度洞察报告 · 多风格可视化看板
数据来源: 本地CSV / Sorftime平台
输出方式: MD报告 + HTML看板(多模板) + 飞书同步(可选)
======================================================================
    """)


def config_wizard(total_available: int,
                  preset_max=None, preset_mode=None, preset_creator=None):
    """
    交互式配置向导（强制交互模式）

    Args:
        total_available: 可用的评论总数
        preset_max: 预设的分析数量（命令行提供）
        preset_mode: 预设的模式（命令行提供）
        preset_creator: 预设的署名（命令行提供）

    Returns:
        tuple: (max_reviews, mode, creator_name)
    """

    # Q1 (打标深度)
    print(f"🚀 欢迎使用电商评论AI深度洞察器 (V1.0 Created By Buluu@新西楼)")
    print(f"📦 [向导 1/3] 文件共有 {total_available} 条有效评论，您计划打标分析多少条？")
    if preset_max is not None:
        print(f"   [当前预设: {preset_max} 条]")
        max_rev_input = input(f"   请输入数量 (直接回车使用预设值 {preset_max} 条) >>> ").strip()
        max_rev = int(max_rev_input) if max_rev_input else preset_max
    else:
        print("   [默认值: 100 条，建议 100-300]")
        max_rev_input = input("   请输入数量 (直接回车使用默认值 100 条) >>> ").strip()
        max_rev = int(max_rev_input) if max_rev_input else 100
    # 确保不超过可用数量
    max_rev = min(max_rev, total_available)

    # Q2 (推理引擎选择)
    print("\n🤖 [向导 2/3] 请选择 AI 引擎组合：")
    print()
    print("   [1] Gemini增强模式（推荐）")
    print("       调用Gemini API")
    print("       使用【Gemini 3.1 flash】生成洞察报告")
    print("       使用【Gemini 3.1 pro】生成可视化看板（需要API Key，产生费用）")
    print()
    print("   [2] Claude CLI+Gemini混动模式")
    print("       文字报告使用Claude Code内置模型")
    print("       可视化看板使用【Gemini 3.1 pro】生成（需要API Key，产生费用）")
    print()
    print("   [3] Claude CLI 本地模式")
    print("       使用您的Claude Code中的内置模型进行打标、推理、报告和看板生成")
    print()
    mode_names = {"1": "Gemini增强", "2": "CLI+Gemini混动", "3": "Claude CLI 全程"}
    if preset_mode is not None:
        print(f"   [当前预设: {mode_names.get(preset_mode, preset_mode)} 模式]")
        mode_input = input(f"   输入编号 [直接回车使用预设值 {preset_mode}] >>> ").strip()
        mode = mode_input if mode_input in ["1", "2", "3"] else preset_mode
    else:
        mode_input = input("   输入编号 [默认值: 1] >>> ").strip()
        mode = mode_input if mode_input in ["1", "2", "3"] else "1"

    # Q3 (报告署名)
    print("\n✍️ [向导 3/3] 报告需要个性化署名吗？")
    if preset_creator is not None:
        print(f"   [当前预设: {preset_creator}]")
        creator_input = input(f"   请输入署名 (直接回车使用预设值 '{preset_creator}') >>> ").strip()
        creator = creator_input if creator_input else preset_creator
    else:
        print("   [留空默认为: AI Assistant]")
        creator_input = input("   请输入署名 (直接回车使用默认值) >>> ").strip()
        creator = creator_input if creator_input else None

    # 打印配置总结
    print("\n" + "=" * 60)
    print("✅ 配置确认：")
    print(f"   📊 分析数量: {max_rev} 条")
    print(f"   🤖 运行模式: {mode_names.get(mode, mode)}")
    print(f"   ✍️  报告署名: {creator or 'AI Assistant'}")
    print("=" * 60 + "\n")

    return (max_rev, mode, creator)


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


def extract_asin_from_file(file_path: str) -> str:
    """从文件名提取 ASIN"""
    filename = Path(file_path).stem
    asin_pattern = r'[A-Z0-9]{10}'
    matches = re.findall(asin_pattern, filename.upper())
    return matches[0] if matches else filename.upper()[:10]


def is_interactive_environment():
    """检测是否在交互式终端环境中运行"""
    return sys.stdin.isatty()


def main():
    """主函数"""

    parser = argparse.ArgumentParser(description="Amazon Review Analyzer V2.0 — Agent 原生版")
    parser.add_argument("input_file", nargs="?", default=None,
                        help="输入 CSV/Excel 文件路径或 URL（使用 --source sorftime 时可省略）")
    # V2.0: 数据来源
    parser.add_argument("--source", choices=["csv", "sorftime"], default="csv",
                        help="数据来源: csv(默认) 或 sorftime")
    parser.add_argument("--asin", help="产品 ASIN（--source sorftime 时必填）")
    parser.add_argument("--site", default="US",
                        help="站点代码（默认 US，可选 UK/DE/JP 等）")
    # V2.0: 模板与输出
    parser.add_argument("--template", default="premium-gold",
                        help="可视化看板模板名称（默认 premium-gold）")
    parser.add_argument("--feishu-sync", action="store_true",
                        help="同步结果到飞书文档（需要 lark-cli）")
    # 原有参数
    parser.add_argument("--engine", choices=["claude", "opencode"], default=None,
                        help="CLI 引擎: claude (默认) 或 opencode")
    parser.add_argument("--max-reviews", type=int, help="分析评论上限", default=None)
    parser.add_argument("--batch-size", type=int, default=20, help="批次大小")
    parser.add_argument("--mode", choices=["1", "2", "3"], default=None,
                        help="分析模式: 1=Gemini增强(需Key), 2=混动(CLI打标+Gemini看板), 3=CLI本地(免费)")
    parser.add_argument("--creator", help="报告署名/品牌", default=None)
    parser.add_argument("--gemini-key", help="Gemini API Key (也可通过环境变量配置)")
    parser.add_argument("--output-dir", help="自定义输出目录")
    args = parser.parse_args()

    # 参数校验
    if args.source == "sorftime" and not args.asin:
        parser.error("--source sorftime 需要 --asin 参数")
    if args.source == "csv" and not args.input_file:
        parser.error("CSV 模式需要提供输入文件路径")

    # 判断是否缺少关键参数
    _missing_params = []
    if args.max_reviews is None:
        _missing_params.append("--max-reviews")
    if args.mode is None:
        _missing_params.append("--mode")
    if args.creator is None:
        _missing_params.append("--creator")
    needs_interaction = len(_missing_params) > 0

    # 非交互环境 + 缺少参数 → 拒绝执行，报错退出
    if needs_interaction and not is_interactive_environment():
        print("=" * 70)
        print("❌ 缺少必要参数，无法在非交互式环境中运行")
        print("=" * 70)
        print()
        print("  缺少以下参数：")
        for p in _missing_params:
            print(f"    ⚠️  {p}")
        print()
        print("  请通过命令行提供完整参数：")
        print(f"    python3 main.py '{args.input_file}' \\")
        print("      --max-reviews 100 \\")
        print("      --mode 1 \\")
        print("      --creator '你的署名'")
        print()
        print("  💡 提示：如需使用交互式菜单，请直接在终端中运行此命令。")
        print("=" * 70)
        sys.exit(1)

    # 打印工具说明（向导第一步）
    print_intro()

    # 处理 --engine 参数
    if args.engine:
        config.CLI_ENGINE = args.engine
        print(f"🔧 CLI 引擎: {config.CLI_ENGINE}")

    # V2.0: 数据获取（支持 Sorftime 或本地 CSV）
    if args.source == "sorftime":
        print(f"\n📡 [数据获取] 从 Sorftime 获取评论数据...")
        print(f"   ASIN: {args.asin}, 站点: {args.site}")
        fetcher = get_fetcher("sorftime")
        if not fetcher.validate_config():
            print("❌ Sorftime 配置无效。请设置 SORFTIME_API_KEY 环境变量。")
            sys.exit(1)
        try:
            csv_path_str = fetcher.fetch(args.asin, fields=None, site=args.site)
            resolved_file = csv_path_str
            print(f"✅ 数据获取完成: {csv_path_str}")
        except Exception as e:
            print(f"❌ Sorftime 数据获取失败: {e}")
            sys.exit(1)
    else:
        # 原有 CSV 路径
        if not args.input_file:
            print("❌ CSV 模式需要提供输入文件路径")
            sys.exit(1)
        resolved_file = download_if_url(args.input_file)

    input_path = Path(resolved_file)
    if not input_path.exists():
        print(f"❌ 错误：找不到文件: {input_path}")
        sys.exit(1)

    # 2. 加载初始数据以获取评论总数
    reviews, original_df = load_reviews_from_file(resolved_file)
    total_available = len(reviews)
    print(f"📄 成功加载表格：检测到 {total_available} 条有效评论记录")

    # 3. 配置合并 (优先级：命令行 > 向导 > 默认)
    if not needs_interaction:
        # 三个参数都已通过命令行提供，跳过向导
        print(f"\n✅ 检测到完整命令行参数，跳过交互式向导")
        max_reviews = args.max_reviews
        mode = args.mode
        creator = args.creator
    else:
        # 在 TTY 环境且缺少参数 → 启动交互式向导
        wizard_max_reviews, wizard_mode, wizard_creator = config_wizard(
            total_available=total_available,
            preset_max=args.max_reviews,
            preset_mode=args.mode,
            preset_creator=args.creator
        )
        print()  # 向导结束后添加空行
        # 向导结果优先
        max_reviews = wizard_max_reviews
        mode = wizard_mode
        creator = wizard_creator

    # 应用配置
    if max_reviews:
        config.MAX_REVIEWS = max_reviews

    if creator:
        config.HTML_CREATOR_NAME = creator

    # Key 处理
    gemini_key = args.gemini_key or os.environ.get("GEMINI_API_KEY") or config.GEMINI_API_KEY
    if gemini_key:
        config.GEMINI_API_KEY = gemini_key

    # 模式分配 (与SKILL.md中的选项顺序一致)
    if mode == "1":
        # 模式1: Gemini增强模式 - 全程使用Gemini API
        config.INSIGHTS_PROVIDER = "gemini"
        config.GEMINI_MODEL = "gemini-3-flash-preview"  # 文字报告专用模型
        config.HTML_GENERATION_SOURCE = "gemini"
        config.HTML_GENERATION_MODEL = "gemini-3.1-pro-preview"  # 可视化看板专用模型
        print("💡 模式：Gemini 增强模式 (Flash报告 + 3.1 Pro看板)")
    elif mode == "2":
        # 模式2: Claude CLI+Gemini混动模式 - 打标用CLI，看板用Gemini
        config.INSIGHTS_PROVIDER = "cli"
        config.HTML_GENERATION_SOURCE = "gemini"
        config.HTML_GENERATION_MODEL = "gemini-3.1-pro-preview"  # 可视化看板专用模型
        print("💡 模式：混动模式 (CLI 打标 + Gemini 3.1 Pro 看板)")
    elif mode == "3":
        # 模式3: Claude CLI 本地模式 - 全程使用本地模型
        config.INSIGHTS_PROVIDER = "cli"
        config.HTML_GENERATION_SOURCE = "local"
        engine_label = "OpenCode" if config.CLI_ENGINE == "opencode" else "Claude CLI"
        print(f"💡 模式：{engine_label} 本地模式 (全本地方案)")

    # 检查 Key 依赖
    if config.HTML_GENERATION_SOURCE == "gemini" and not config.GEMINI_API_KEY:
        print("⚠️  警告：选择了 Gemini 模式但未配置 API Key。将回退至本地渲染。")
        config.HTML_GENERATION_SOURCE = "local"

    # 应用自定义输出目录
    if args.output_dir:
        output_path = Path(args.output_dir)
        if output_path.exists() and output_path.is_file():
            print(f"❌ 错误：输出路径是一个文件，不是目录: {output_path}")
            sys.exit(1)
        config.OUTPUT_DIR = output_path
        # 确保输出目录存在
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"📁 自定义输出目录: {config.OUTPUT_DIR}")

    asin = args.asin if args.source == "sorftime" else extract_asin_from_file(resolved_file)

    # 截断评论
    if len(reviews) > config.MAX_REVIEWS:
        print(f"✂️  评论总数 {len(reviews)} 超过上限，截取前 {config.MAX_REVIEWS} 条")
        reviews = reviews[:config.MAX_REVIEWS]

    try:
        # ========== 执行全流程 ==========

        # Phase 1: AI 深度打标分析
        print(f"\n🧠 [Phase 1/4] 评论AI深度打标分析中...")
        tagged_reviews = analyze_all(reviews, batch_size=args.batch_size)
        print(f"✅ [Phase 1/4] 评论打标完成！成功分析 {len(tagged_reviews)} 条评论\n")

        # Phase 2: 用户画像识别与降级逻辑配置
        print(f"👥 [Phase 2/4] 用户画像识别与降级逻辑配置中...")
        print(f"   - 正在分析 {len(tagged_reviews)} 条打标评论...")
        print(f"   - 识别用户画像中...")
        personas, golden_samples = analyze_user_personas(tagged_reviews)
        print(f"✅ [Phase 2/4] 用户画像识别完成！识别到 {len(personas)} 个画像，{len(golden_samples)} 条黄金样本\n")

        # Phase 3: AI 撰写深度战略洞察报告
        print(f"📝 [Phase 3/4] AI深度战略洞察报告生成中...")
        print(f"   - 正在生成 {len(personas)} 个用户画像分析...")
        if config.INSIGHTS_PROVIDER == "gemini":
            print(f"   - 使用引擎: Gemini API ({config.GEMINI_MODEL})")
            print(f"   - 正在调用 Gemini API 生成洞察...")
        else:
            print(f"   - 使用引擎: Claude Code CLI")
            print(f"   - 正在调用 Claude CLI 生成洞察...")
        stats = calculate_stats_summary(tagged_reviews)
        insights_md = generate_insights(
            stats=stats,
            personas=personas,
            golden_samples=golden_samples,
            asin=asin
        )
        if insights_md:
            print(f"✅ [Phase 3/4] 洞察报告已生成！字数约 {len(insights_md):,} 字\n")
        else:
            print(f"⚠️ [Phase 3/4] 洞察报告生成失败\n")

        # 保存 Markdown
        md_path = config.get_md_path(asin)
        if insights_md:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(insights_md)

        # 保存 CSV
        csv_path = save_tagged_reviews_to_csv(tagged_reviews, asin)

        # Phase 4: 渲染可视化看板
        if config.HTML_GENERATION_SOURCE == "gemini":
            print(f"🎨 [Phase 4/4] 可视化看板渲染中...")
            print(f"   - 使用引擎: Gemini {config.HTML_GENERATION_MODEL}")
            print(f"   - 正在调用 Gemini API 生成HTML...")
            print(f"   - 预计需要 3-5 分钟，请耐心等待...")
        else:
            print(f"🎨 [Phase 4/4] 可视化看板渲染中...")
            print(f"   - 使用引擎: 本地模板 (黑金看板)")
            print(f"   - 正在渲染本地模板...")

        summary = {
            "total": len(tagged_reviews),
            "tagged": stats["tagged"],
            "persona_count": len(personas),
            "avg_rating": stats.get("avg_rating", 0),
            "sentiment": stats.get("sentiment", {}),
            "top_tags": stats.get("top_tags", {})
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
        print(f"✅ [Phase 4/5] 可视化看板构建完成！文件: {html_path.name}\n")

        # Phase 5 (V2.0): 输出管理 — 使用 OutputManager 生成完整输出
        print(f"📦 [Phase 5/5] 生成完整输出包...")
        from src.output_manager import generate_outputs, select_template

        # 选择模板
        template_name = args.template
        # 如果模板不存在，使用默认
        try:
            from src.template_engine import list_templates as _lt
            available = [t["name"] for t in _lt()]
            if template_name not in available:
                print(f"   ⚠️ 模板 '{template_name}' 不存在，使用默认模板")
                template_name = available[0] if available else "premium-gold"
        except Exception:
            pass

        # 准备分析数据给 OutputManager
        analysis_data_for_output = {
            "asin": asin,
            "product_name": asin,
            "total_reviews": len(tagged_reviews),
            "avg_rating": stats.get("avg_rating", 0),
            "summary": summary,
            "sentiment": stats.get("sentiment", {}),
            "sentiment_distribution": stats.get("sentiment", {}),
            "tag_statistics": stats.get("top_tags", {}),
            "top_tags": stats.get("top_tags", {}),
            "personas": [{"name": p.get("name", ""), "count": p.get("count", 0), "tags": p.get("tags", {})} for p in personas],
            "golden_samples": golden_samples,
            "insights_md": insights_md,
            "statistics": stats,
        }

        output_config = {
            "template_name": template_name,
            "sync_feishu": args.feishu_sync,
            "output_dir": str(config.OUTPUT_DIR),
            "asin": asin,
            "creator": config.HTML_CREATOR_NAME,
        }

        output_results = generate_outputs(analysis_data_for_output, output_config)

        # 飞书同步结果
        feishu_result = output_results.get("feishu_result", {})
        if args.feishu_sync:
            if feishu_result and feishu_result.get("success"):
                print(f"   ✅ 飞书同步成功！")
                if feishu_result.get("doc_url"):
                    print(f"   📄 文档: {feishu_result['doc_url']}")
                wb_count = feishu_result.get("whiteboard_count", 0)
                if wb_count > 0:
                    print(f"   📊 白板图表: {wb_count} 个已渲染")
            else:
                error = feishu_result.get("error", "未知错误") if feishu_result else "同步失败"
                print(f"   ⚠️ 飞书同步失败: {error}")
                print(f"   💡 本地文件已安全生成，不影响使用")

        # 最终输出结果
        final_md = output_results.get("md_path", str(md_path))
        final_html = output_results.get("html_path", str(html_path))

        print("\n" + "✨" * 30)
        print("🎉 分析任务圆满完成！")
        print(f"  - 洞察报告: {Path(final_md).name}")
        print(f"  - 结构数据: {csv_path.name}")
        print(f"  - 可视化看板: {Path(final_html).name} (模板: {template_name})")
        if args.feishu_sync and feishu_result and feishu_result.get("doc_url"):
            print(f"  - 飞书文档: {feishu_result['doc_url']}")
            wb_count = feishu_result.get("whiteboard_count", 0)
            if wb_count > 0:
                print(f"  - 白板图表: {wb_count} 个")
        print("✨" * 30 + "\n")

    except Exception as e:
        print(f"\n❌ 引擎崩溃: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

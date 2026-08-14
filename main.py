#!/usr/bin/env python3
"""
Amazon 商品评论 AI 深度分析工具 - 主入口 V2.0 (Agent 原生版)
功能：支持交互式向导 + 全参数驱动 + 卖家精灵数据对接 + 多模板看板 + 飞书同步
"""

import sys
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 导入核心模块
from src.data_loader import load_reviews_from_file, download_if_url
from src.review_analyzer import analyze_all
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, generate_insights
from src.config import config
from src.pipeline_common import (
    extract_asin_from_file,
    run_output_phase,
)
from src import agent_pipeline

# V2.0 新模块
from src.data_fetchers import get_fetcher, list_fetchers
from src.output_manager import OutputManager
from src.prompts.manager import list_chapters


def print_intro():
    """打印工具详细说明"""
    print("""
🚀 多场景评论内容 AI 深度分析工具 V2.0 — Agent 原生版 Created By Buluu@新西楼
======================================================================
核心功能: 22维度智能标签 · 15章深度洞察报告 · 多风格可视化看板
数据来源: 本地CSV(主源) / 卖家精灵(可选增强)
输出方式: MD报告 + HTML看板(多模板) + 飞书同步(可选)
======================================================================
    """)


def config_wizard(total_available: int,
                  preset_max=None, preset_creator=None):
    """
    交互式配置向导（强制交互模式）

    Args:
        total_available: 可用的评论总数
        preset_max: 预设的分析数量（命令行提供）
        preset_creator: 预设的署名（命令行提供）

    Returns:
        tuple: (max_reviews, creator)
    """

    # Q1 (打标深度)
    print(f"🚀 欢迎使用电商评论AI深度洞察器 (V2.0 Created By Buluu@新西楼)")
    print(f"📦 [向导 1/2] 文件共有 {total_available} 条有效评论，您计划打标分析多少条？")
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

    # Q2 (报告署名)
    print("\n✍️ [向导 2/2] 报告需要个性化署名吗？")
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
    print(f"   🤖 运行模式: CLI 本地模式")
    print(f"   ✍️  报告署名: {creator or 'AI Assistant'}")
    print("=" * 60 + "\n")

    return (max_rev, creator)


def is_interactive_environment():
    """检测是否在交互式终端环境中运行"""
    return sys.stdin.isatty()


def main():
    """主函数"""

    parser = argparse.ArgumentParser(description="Amazon Review Analyzer V2.0 — Agent 原生版")
    parser.add_argument("input_file", nargs="?", default=None,
                        help="输入 CSV/Excel 文件路径或 URL（使用 --source sellersprite 时可省略）")
    # V2.0: 数据来源
    parser.add_argument("--source", choices=["csv", "sellersprite"], default="csv",
                        help="数据来源: csv(默认) 或 sellersprite")
    parser.add_argument("--asin", help="产品 ASIN（--source sellersprite 时必填）")
    parser.add_argument("--site", default="US",
                        help="站点代码（默认 US，可选 UK/DE/JP 等）")
    # V2.0: 模板与输出
    parser.add_argument("--template", default="premium-gold",
                        help="可视化看板模板名称（默认 premium-gold，传 none 跳过HTML生成）")
    parser.add_argument("--feishu-sync", action="store_true",
                        help="同步结果到飞书文档（需要 lark-cli）")
    # 原有参数
    parser.add_argument("--engine", choices=["claude", "opencode"], default=None,
                        help="CLI 引擎: claude (默认) 或 opencode（仅 --llm cli 模式生效）")
    parser.add_argument("--llm", choices=["cli", "agent"], default="cli",
                        help="LLM 执行模式: cli(默认, subprocess 调宿主 CLI 引擎) 或 "
                             "agent(宿主 Agent 自执行打标与报告撰写, 见 src/agent_pipeline.py)")
    parser.add_argument("--resume", default=None, metavar="WORKDIR",
                        help="Agent 模式推进: 恢复 --llm agent 准备的工作目录"
                             "（此模式下忽略其它参数，可重复调用）")
    parser.add_argument("--max-reviews", type=int, help="分析评论上限", default=None)
    parser.add_argument("--batch-size", type=int, default=20, help="批次大小")
    parser.add_argument("--concurrent", type=int, default=None,
                        help="最大并发批次数 (默认4, 上限8)")
    parser.add_argument("--creator", help="报告署名/品牌", default=None)
    parser.add_argument("--output-dir", help="自定义输出目录")
    args = parser.parse_args()

    # --resume 模式：Agent 自执行流水线推进状态机（忽略其它参数）
    if args.resume:
        agent_pipeline.resume(args.resume)
        return

    # 参数校验
    if args.source == "sellersprite" and not args.asin:
        parser.error("--source sellersprite 需要 --asin 参数")
    if args.source == "csv" and not args.input_file:
        parser.error("CSV 模式需要提供输入文件路径")

    # 判断是否缺少关键参数
    _missing_params = []
    if args.max_reviews is None:
        _missing_params.append("--max-reviews")
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

    # V2.0: 数据获取（CSV 主源 或 卖家精灵可选增强）
    if args.source == "sellersprite":
        print(f"\n📡 [数据获取] 从卖家精灵获取评论数据...")
        print(f"   ASIN: {args.asin}, 站点: {args.site}")
        print(f"   ⚠️  卖家精灵为可选增强源：覆盖量有限、部分评论正文可能缺失，深度分析建议用 CSV")
        fetcher = get_fetcher("sellersprite")
        if not fetcher.validate_config():
            print("❌ 卖家精灵配置无效。请设置 SELLERSPRITE_SECRET_KEY 环境变量。")
            sys.exit(1)
        try:
            csv_path_str = fetcher.fetch(args.asin, fields=None, site=args.site)
            resolved_file = csv_path_str
            print(f"✅ 数据获取完成: {csv_path_str}")
        except Exception as e:
            print(f"❌ 卖家精灵数据获取失败: {e}")
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
        # 两个参数都已通过命令行提供，跳过向导
        print(f"\n✅ 检测到完整命令行参数，跳过交互式向导")
        max_reviews = args.max_reviews
        creator = args.creator
    else:
        # 在 TTY 环境且缺少参数 → 启动交互式向导
        wizard_max_reviews, wizard_creator = config_wizard(
            total_available=total_available,
            preset_max=args.max_reviews,
            preset_creator=args.creator
        )
        print()  # 向导结束后添加空行
        # 向导结果优先
        max_reviews = wizard_max_reviews
        creator = wizard_creator

    # 应用配置
    if max_reviews:
        config.MAX_REVIEWS = max_reviews

    if creator:
        config.HTML_CREATOR_NAME = creator

    # 并发数配置
    if args.concurrent:
        config.MAX_CONCURRENT_AGENTS = args.concurrent

    # 运行模式提示（cli=subprocess 调 CLI 引擎 / agent=宿主 Agent 自执行）
    if args.llm == "agent":
        print(f"💡 模式：Agent 自执行模式 (打标与报告由宿主 Agent 完成，不依赖 CLI 引擎)")
    else:
        if config.CLI_ENGINE == "none":
            print("=" * 70)
            print("❌ 当前无可用的 CLI 引擎（未检测到 claude / opencode），--llm cli 模式无法执行")
            print("=" * 70)
            print()
            print("  💡 两种解决方案：")
            print("     1. 安装 Claude Code 或 OpenCode 并加入 PATH 后重试")
            print("     2. 改用 Agent 自执行模式，由宿主 Agent 完成打标与报告撰写：")
            if args.input_file:
                print(f"        python3 main.py '{args.input_file}' --llm agent \\")
            else:
                print(f"        python3 main.py --source sellersprite --asin {args.asin} --llm agent \\")
            print("          --max-reviews 100 --creator '你的署名'")
            print("=" * 70)
            sys.exit(1)
        engine_label = "OpenCode" if config.CLI_ENGINE == "opencode" else "Claude CLI"
        print(f"💡 模式：{engine_label} 本地模式 (全本地方案)")
        print(f"🔧 并发线程数: {config.MAX_CONCURRENT_AGENTS}")

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

    asin = args.asin if args.source == "sellersprite" else extract_asin_from_file(resolved_file)

    # 截断评论
    if len(reviews) > config.MAX_REVIEWS:
        print(f"✂️  评论总数 {len(reviews)} 超过上限，截取前 {config.MAX_REVIEWS} 条")
        reviews = reviews[:config.MAX_REVIEWS]

    # Agent 自执行模式：参数校验/数据获取/加载/截断已完成，
    # 到此为止 Python 侧工作结束，打标与报告由宿主 Agent 完成
    if args.llm == "agent":
        agent_pipeline.prepare(
            reviews=reviews,
            asin=asin,
            source=args.source,
            original_file=str(resolved_file),
            batch_size=args.batch_size,
            template=args.template,
            feishu_sync=args.feishu_sync,
        )
        return

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
        print(f"   - 使用引擎: {engine_label}")
        stats = calculate_stats_summary(tagged_reviews)

        # 异常信号检测（确定性规则引擎，零 LLM 成本）
        from src.anomaly_detector import detect_anomalies
        anomaly_context = {
            "has_review_date": any(
                r.get("date") and str(r.get("date")).strip() not in ("", "nan", "None", "null")
                for r in tagged_reviews
            )
        }
        anomaly_signals = detect_anomalies(tagged_reviews, stats, anomaly_context)
        if anomaly_signals:
            print(f"   ⚠️  检测到 {len(anomaly_signals)} 条异常信号: "
                  f"{', '.join(f'{s.signal_type}[{s.severity}]' for s in anomaly_signals)}")

        insights_md = generate_insights(
            stats=stats,
            personas=personas,
            golden_samples=golden_samples,
            asin=asin,
            anomaly_signals=anomaly_signals,
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

        # Phase 4 (V2.0): 输出管理 — 统一生成 CSV + MD + HTML看板 + 飞书同步
        # （共享函数，agent 自执行模式收尾阶段复用同一实现）
        run_output_phase(
            tagged_reviews=tagged_reviews,
            stats=stats,
            personas=personas,
            golden_samples=golden_samples,
            insights_md=insights_md or "",
            asin=asin,
            template_name=args.template,
            feishu_sync=args.feishu_sync,
        )

    except Exception as e:
        print(f"\n❌ 引擎崩溃: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

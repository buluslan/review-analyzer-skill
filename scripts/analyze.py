import os
import sys
import subprocess
import argparse

def print_banner():
    """打印工具综述横幅"""
    print("""
🚀 Amazon 商品评论 AI 深度分析工具 V1.0
============================================================

工具定义: 电商评论AI深度洞察器 (V1.0 Created By Buluu@新西楼)
核心产出: 针对您提供的原始评论数据，逐条进行 22 个维度标签挖掘、
          生成深度洞察分析文字报告、高品质的可视化看板

运行模式:
  [1] 全程使用内置模型
      → 使用 Claude CLI 内置模型，不消耗额外 API 额度
      → 通过内置本地模板生成可视化看板（离线可用）

  [2] 文字报告内置 + 可视化 Gemini（推荐）
      → 文字分析使用内置模型（节省成本）
      → 可视化看板使用 Gemini 3.1 Pro（最高视觉质感）
      → 需配置 Gemini API Key

  [3] 全程 Gemini AI 驱动（最高质量）
      → 文字报告使用 Gemini 3.1 Flash
      → 可视化看板使用 Gemini 3.1 Pro
      → 最高推理质量，需全程消耗 API 额度

默认配置: 标签挖掘环节统一使用内置模型（最高效率）

============================================================
""")

def run_wizard():
    """交互式向导（当没有提供必需参数时）"""
    print_banner()

    # Q1: 文件路径
    while True:
        input_file = input("📦 请提供要分析的评论文件路径: ").strip()
        if input_file:
            if os.path.exists(input_file):
                break
            else:
                print(f"   ⚠️  文件不存在: {input_file}")
                print(f"   请检查路径后重试")
        else:
            print("   ⚠️  请输入有效的文件路径")

    # Q2: 分析数量
    while True:
        max_reviews = input("📊 分析多少条评论？[默认 100]: ").strip() or "100"
        try:
            max_reviews = int(max_reviews)
            if max_reviews > 0:
                break
            else:
                print("   ⚠️  请输入大于 0 的数字")
        except ValueError:
            print("   ⚠️  请输入有效的数字")

    # Q3: 模式选择
    print("\n🤖 请选择 AI 调度组合：")
    print("   [1] 全程使用内置模型（不消耗 API 额度）")
    print("   [2] 文字报告内置 + 可视化 Gemini（推荐）")
    print("   [3] 全程 Gemini AI 驱动（最高质量）")

    while True:
        mode = input("   输入编号 [默认 1]: ").strip() or "1"
        if mode in ["1", "2", "3"]:
            break
        else:
            print("   ⚠️  请输入 1、2 或 3")

    # Q4: 报告署名
    creator = input("\n✍️ 报告署名 [默认 AI Assistant]: ").strip() or "AI Assistant"

    print("\n✅ 配置完成，开始分析...")
    print("-" * 60)

    return {
        "input_file": input_file,
        "max_reviews": max_reviews,
        "mode": mode,
        "creator": creator
    }

def find_main_project():
    """查找主项目路径"""
    possible_paths = [
        os.environ.get("REVIEW_ANALYZER_PATH"),
        "../review-analyzer-skill",
        "../review-analyzer",
        "./review-analyzer-skill"
    ]

    # 首先检查环境变量和标准路径
    for path in possible_paths:
        if path and os.path.exists(os.path.join(path, "main.py")):
            return path

    # 尝试从脚本位置相对查找
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rel_paths = [
        os.path.join(script_dir, "../../review-analyzer-skill"),
        os.path.join(script_dir, "../review-analyzer-skill"),
        os.path.join(script_dir, "./review-analyzer-skill"),
    ]

    for rel_path in rel_paths:
        if os.path.exists(os.path.join(rel_path, "main.py")):
            return rel_path

    # 未找到，给出清晰的提示
    print("❌ 错误：无法找到主项目")
    print("请确保主项目 'review-analyzer-skill' 在以下位置之一：")
    print("  1. 环境变量 REVIEW_ANALYZER_PATH 指定的路径")
    print("  2. ../review-analyzer-skill/")
    print("  3. ../review-analyzer/")
    print("  4. ./review-analyzer-skill/")
    print("\n或者通过以下方式指定主项目路径：")
    print("  export REVIEW_ANALYZER_PATH=/path/to/review-analyzer-skill")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Review Analyzer Skill Bridge - 支持3种使用模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  1. 交互式模式（人类用户直接运行）:
     python scripts/analyze.py

  2. AI Agent 调用（通过命令行参数）:
     python scripts/analyze.py data.csv --max-reviews 100 --mode 1

  3. 高级用户/脚本（跳过交互）:
     python scripts/analyze.py data.csv --max-reviews 100 --mode 1 --creator "Name" --no-wizard
        """
    )
    parser.add_argument("input", nargs='?', help="输入文件路径（CSV/Excel）")
    parser.add_argument("--max-reviews", type=int, default=100, help="分析的最大评论数 [默认: 100]")
    parser.add_argument("--mode", choices=["1", "2", "3"], default="1",
                        help="分析模式: 1=内置模型, 2=混合模式, 3=全程Gemini [默认: 1]")
    parser.add_argument("--creator", default="AI Assistant", help="报告署名 [默认: AI Assistant]")
    parser.add_argument("--gemini-key", help="Gemini API Key（覆盖 .env 配置）")
    parser.add_argument("--output", help="自定义输出目录")
    parser.add_argument("--no-wizard", action="store_true",
                       help="跳过交互式向导（用于脚本调用）")

    args = parser.parse_args()

    # 场景判断：是否需要运行交互式向导
    # 情况1：没有提供输入文件 → 必须运行向导
    # 情况2：明确指定了 --no-wizard → 跳过向导（需有输入文件）
    # 情况3：提供了输入文件但没有 --no-wizard → 运行向导但可跳过（AI Agent 调用场景）
    need_wizard = False

    if not args.input:
        # 没有输入文件，必须运行向导
        need_wizard = True
    elif not args.no_wizard:
        # 有输入文件但没有 --no-wizard 标志，尝试运行向导
        # 检测是否在交互式环境中
        if sys.stdin.isatty():
            need_wizard = True
        else:
            # 非交互式环境（如 AI Agent 调用），使用命令行参数
            need_wizard = False

    # 运行交互式向导（如果需要）
    if need_wizard:
        try:
            wizard_args = run_wizard()
            # 向导返回的参数覆盖命令行参数
            args.input = wizard_args.get("input_file", args.input)
            args.max_reviews = wizard_args.get("max_reviews", args.max_reviews)
            args.mode = wizard_args.get("mode", args.mode)
            args.creator = wizard_args.get("creator", args.creator)
        except (EOFError, KeyboardInterrupt):
            # 用户中断或非交互式环境
            print("\n⚠️  向导已取消")
            if not args.input:
                print("❌ 错误：非交互式环境需要提供输入文件")
                print("提示: 使用 --no-wizard 跳过向导，或提供完整的命令行参数")
                print("示例: python scripts/analyze.py data.csv --max-reviews 100 --mode 1 --no-wizard")
                sys.exit(1)

    # 最终验证：确保有输入文件
    if not args.input:
        print("❌ 错误：未提供输入文件")
        print("\n使用方法:")
        print("  python scripts/analyze.py <文件路径> [选项]")
        print("\n运行 'python scripts/analyze.py --help' 查看详细帮助")
        sys.exit(1)

    # 验证输入文件存在
    if not os.path.exists(args.input):
        print(f"❌ 错误：输入文件不存在: {args.input}")
        sys.exit(1)

    # 查找主项目路径
    main_project_dir = find_main_project()
    main_script = os.path.abspath(os.path.join(main_project_dir, "main.py"))

    # 构建命令
    cmd = [sys.executable, main_script, args.input]
    cmd.extend(["--max-reviews", str(args.max_reviews)])
    cmd.extend(["--mode", args.mode])

    if args.creator:
        cmd.extend(["--creator", args.creator])
    if args.gemini_key:
        cmd.extend(["--gemini-key", args.gemini_key])
    if args.output:
        cmd.extend(["--output-dir", args.output])

    # 打印执行信息
    cmd_str = ' '.join(cmd)
    print(f"🔧 执行命令: {cmd_str}")
    print(f"📁 输入文件: {args.input}")
    print(f"📊 分析数量: {args.max_reviews}")
    print(f"🤖 运行模式: {args.mode} ({'内置模型' if args.mode == '1' else '混合模式' if args.mode == '2' else '全程 Gemini'})")
    if args.creator != "AI Assistant":
        print(f"✍️ 报告署名: {args.creator}")
    print("-" * 60)

    try:
        # 执行主项目脚本
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ 分析完成！")
        print("=" * 60)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print(f"❌ 分析失败，退出码: {e.returncode}")
        print("=" * 60)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("⚠️  用户中断执行")
        print("=" * 60)
        sys.exit(130)

if __name__ == "__main__":
    main()

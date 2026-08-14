"""
Agent 自执行流水线模块 V2.1

Python 只负责确定性工序（数据加载/分批/统计/异常检测/输出包），
LLM 工序（评论打标、15 章报告撰写）由宿主 Agent 自己完成：
  1. prepare()：加载数据 → 分批 → 写 prompt 文件 → 打印待办清单后退出
  2. 宿主 Agent 逐批读 tagging/batch_XXX_prompt.md，把 JSON 结果写到同名 .json
  3. resume() 第一次推进：校验打标 → 中间产出 → 写 report_prompt.md 后退出
  4. 宿主 Agent 读 report_prompt.md，把完整报告写到 report_draft.md
  5. resume() 第二次推进：收尾 → MD/CSV/HTML 看板/飞书

工作目录约定: {config.OUTPUT_DIR}/agent_work_{ASIN}/
  - state.json          流水线状态（phase 状态机，幂等可重复 resume）
  - reviews.json        prepare 阶段截断后的原始评论列表
  - tagging/            各批次 prompt 与宿主 Agent 写回的打标结果
  - report_prompt.md    报告撰写 prompt（resume 中间阶段生成）
  - report_draft.md     宿主 Agent 写的报告草稿

与 CLI 模式（review_analyzer.analyze_all / insights_generator._generate_via_cli）
同构：打标解析复用 _parse_batch_response，报告后处理复用 _ensure_mermaid_charts
与 strategic_json 剥离逻辑，保证两种模式产出一致。
"""

import json
import sys
from pathlib import Path

from src.config import config
from src.prompts.manager import build_tagging_prompt, build_insights_prompt
from src.review_analyzer import _parse_batch_response
from src.user_persona_analyzer import analyze_user_personas
from src.insights_generator import calculate_stats_summary, _ensure_mermaid_charts
from src.anomaly_detector import detect_anomalies
from src import insights_generator
from src import pipeline_common

# 工作目录内的固定文件名
STATE_FILE = "state.json"
REVIEWS_FILE = "reviews.json"
REPORT_PROMPT_FILE = "report_prompt.md"
REPORT_DRAFT_FILE = "report_draft.md"
TAGGING_DIR = "tagging"

# 状态机 phase 值
PHASE_AWAIT_TAGGING = "await_tagging"   # 等待宿主 Agent 完成打标
PHASE_AWAIT_REPORT = "await_report"     # 等待宿主 Agent 撰写报告
PHASE_DONE = "done"                     # 全部完成


# ==================== 工具函数 ====================


def _json_default(obj):
    """json.dumps 的兜底序列化：处理 pandas/numpy 标量与其它不可序列化对象。"""
    if hasattr(obj, "item"):  # numpy 标量
        try:
            return obj.item()
        except Exception:
            pass
    return str(obj)


def _write_json(path: Path, data) -> None:
    """写 JSON 文件（utf-8，带 numpy 兜底序列化）。"""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def _read_json(path: Path):
    """读 JSON 文件。"""
    return json.loads(path.read_text(encoding="utf-8"))


def _batch_prompt_files(workdir: Path):
    """列出工作目录下所有打标 prompt 文件（按批次编号排序）。"""
    tagging_dir = workdir / TAGGING_DIR
    if not tagging_dir.exists():
        return []
    return sorted(tagging_dir.glob("batch_*_prompt.md"))


def _batch_result_file(prompt_file: Path) -> Path:
    """根据 prompt 文件名推导对应的打标结果文件名。

    batch_001_prompt.md → batch_001.json
    """
    return prompt_file.with_name(prompt_file.name.replace("_prompt.md", ".json"))


def _chunk_reviews(reviews: list, batch_size: int) -> list:
    """将评论列表按批次大小分组（与 review_analyzer._chunk_reviews 同构）。"""
    batches = []
    for i in range(0, len(reviews), batch_size):
        batches.append(reviews[i:i + batch_size])
    return batches


def _merge_tagged_reviews(workdir: Path, reviews: list, batch_size: int) -> list:
    """校验并合并所有批次的打标结果。

    逐批读取 tagging/batch_XXX.json，用 _parse_batch_response 解析合并
    （与 CLI 模式同构：sentiment/info_score/tags 回填到对应评论条目）。

    Args:
        workdir: 工作目录
        reviews: reviews.json 加载出的原始评论列表
        batch_size: 分批大小

    Returns:
        合并后的 tagged_reviews 列表。

    Raises:
        SystemExit: 批次结果缺失或解析失败时，列出问题批次并以退出码 2 退出。
    """
    prompt_files = _batch_prompt_files(workdir)
    if not prompt_files:
        print("❌ 工作目录中未找到任何打标 prompt 文件（tagging/batch_*_prompt.md）")
        sys.exit(2)

    batches = _chunk_reviews(reviews, batch_size)
    if len(prompt_files) != len(batches):
        print(f"❌ prompt 文件数 ({len(prompt_files)}) 与分批数 ({len(batches)}) 不一致，"
              f"工作目录可能已损坏，请重新运行 --llm agent 准备阶段")
        sys.exit(2)

    missing = []
    parse_failed = []
    tagged_reviews = []

    for idx, (prompt_file, batch) in enumerate(zip(prompt_files, batches)):
        result_file = _batch_result_file(prompt_file)
        if not result_file.exists():
            missing.append(result_file.name)
            continue
        try:
            text = result_file.read_text(encoding="utf-8")
            tagged_reviews.extend(_parse_batch_response(text, batch))
        except Exception as e:
            parse_failed.append((result_file.name, str(e)))

    if missing:
        print("❌ 以下批次的打标结果缺失，请宿主 Agent 补齐后重新运行 --resume：")
        for name in missing:
            print(f"   ⚠️  {TAGGING_DIR}/{name}")
        sys.exit(2)

    if parse_failed:
        print("❌ 以下批次的打标结果解析失败，请宿主 Agent 重写对应 JSON 后重新运行 --resume：")
        for name, err in parse_failed:
            print(f"   ⚠️  {TAGGING_DIR}/{name}: {err}")
        sys.exit(2)

    return tagged_reviews


def _run_deterministic_analysis(tagged_reviews: list):
    """从已合并的打标结果重算确定性中间产物（纯 Python，成本零）。

    包含：用户画像 + 黄金样本、统计摘要、异常信号。
    resume 的中间阶段与收尾阶段各跑一次，保证跨调用无需持久化中间产物
    （避免 pickle 版本坑，golden_samples 也包含在 tagged_reviews 内）。

    Returns:
        (personas, golden_samples, stats, anomaly_signals) 四元组
    """
    personas, golden_samples = analyze_user_personas(tagged_reviews)
    stats = calculate_stats_summary(tagged_reviews)

    # 异常信号检测：has_review_date 判定逻辑与 main.py / generate_from_tagged.py 一致
    anomaly_context = {
        "has_review_date": any(
            r.get("date") and str(r.get("date")).strip() not in ("", "nan", "None", "null")
            for r in tagged_reviews
        )
    }
    anomaly_signals = detect_anomalies(tagged_reviews, stats, anomaly_context)

    return personas, golden_samples, stats, anomaly_signals


def _build_report_prompt(tagged_reviews, personas, golden_samples, stats, anomaly_signals, asin):
    """构建洞察报告 prompt。

    参数与 insights_generator.generate_insights 内部完全一致：
    stats/personas/samples/asin/product_name=None/context（含 has_review_date 逻辑）/anomaly_signals
    """
    context = {}
    # 与 generate_insights 一致：以黄金样本中是否存在日期数据决定时间趋势章节
    has_date = any(
        r.get("date") and r.get("date") not in ("", "nan", "None")
        for r in golden_samples
    )
    if has_date:
        context["has_review_date"] = True
        context["time_distribution_text"] = "用户评论包含日期信息，可进行时间趋势分析"

    return build_insights_prompt(
        stats=stats,
        personas=personas,
        samples=golden_samples,
        asin=asin,
        product_name=None,
        context=context,
        anomaly_signals=anomaly_signals,
    )


# ==================== 入口：prepare ====================


def prepare(
    reviews: list,
    asin: str,
    source: str = "csv",
    original_file: str = "",
    batch_size: int = 20,
    template=None,
    feishu_sync: bool = False,
) -> Path:
    """Agent 模式准备阶段：加载数据、分批、写 prompt 文件。

    数据获取/加载/截断由 main.py 完成（与 CLI 模式共用同一段流程），
    此处只做分批与工作目录初始化，然后打印待办清单后返回。

    Args:
        reviews: 已截断后的原始评论列表（完整 dict，含 _original_data）
        asin: 产品 ASIN
        source: 数据来源（csv / sellersprite）
        original_file: 原始数据文件路径（ sellersprite 为拉取后的 CSV 路径）
        batch_size: 批次大小（agent 模式允许 <20 的小批次，无 20-50 校验）
        template: 可视化看板模板名称（原样保存，收尾阶段归一化）
        feishu_sync: 是否同步飞书

    Returns:
        工作目录 Path: {config.OUTPUT_DIR}/agent_work_{ASIN}/
    """
    if not reviews:
        print("❌ 评论列表为空，无法准备 Agent 工作目录")
        sys.exit(1)

    if batch_size < 1:
        batch_size = 1

    workdir = config.OUTPUT_DIR / f"agent_work_{asin}"
    tagging_dir = workdir / TAGGING_DIR
    tagging_dir.mkdir(parents=True, exist_ok=True)

    # 保存截断后的原始评论（完整 dict，含 _original_data）
    _write_json(workdir / REVIEWS_FILE, reviews)

    # 分批并生成各批次 prompt
    batches = _chunk_reviews(reviews, batch_size)
    prompt_files = []
    for i, batch in enumerate(batches, 1):
        prompt = build_tagging_prompt(batch)
        prompt_file = tagging_dir / f"batch_{i:03d}_prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        prompt_files.append(prompt_file)

    # 写状态文件
    state = {
        "asin": asin,
        "source": source,
        "original_file": str(original_file),
        "batch_size": batch_size,
        "template": template,
        "creator": config.HTML_CREATOR_NAME,
        "feishu_sync": bool(feishu_sync),
        "total_reviews": len(reviews),
        "phase": PHASE_AWAIT_TAGGING,
        # 输出目录快照：resume 是独立进程，需据此恢复 --output-dir 配置
        "output_dir": str(config.OUTPUT_DIR),
    }
    _write_json(workdir / STATE_FILE, state)

    # 打印待办清单（宿主 Agent 的操作指引）
    print("\n" + "=" * 70)
    print(f"🤖 [Agent 自执行模式] 准备阶段完成！共 {len(reviews)} 条评论，"
          f"分为 {len(batches)} 个批次")
    print(f"📁 工作目录: {workdir}")
    print("=" * 70)
    print("\n📝 宿主 Agent 待办清单（第 1/3 步：评论打标）：")
    print("   1. 逐个读取以下 prompt 文件，严格按 prompt 指令打标：")
    for pf in prompt_files:
        print(f"      - {pf}")
    print("   2. 把每批的 JSON 数组结果写到同名 .json 文件，例如：")
    print(f"      {prompt_files[0]} → {_batch_result_file(prompt_files[0])}")
    print("   3. 全部批次完成后，运行以下命令推进：")
    print(f"      python3 main.py --resume {workdir}")
    print("=" * 70 + "\n")

    return workdir


# ==================== 入口：resume ====================


def resume(workdir_str: str) -> None:
    """Agent 模式推进阶段（幂等状态机，可重复调用）。

    状态流转：
      await_tagging → (校验打标) → await_report → (读报告草稿) → done

    Args:
        workdir_str: prepare 返回的工作目录路径
    """
    workdir = Path(workdir_str).expanduser().resolve()
    state_file = workdir / STATE_FILE

    if not state_file.exists():
        print(f"❌ 无效的工作目录（缺少 {STATE_FILE}）: {workdir}")
        sys.exit(2)

    state = _read_json(state_file)
    asin = state["asin"]

    # 恢复 prepare 阶段的配置（resume 是独立进程，config 回到默认值）
    # - 输出目录：优先 state 快照，兜底用工作目录的父目录
    # - 署名：收尾阶段的 MD/看板消费
    output_dir = state.get("output_dir") or str(workdir.parent)
    config.OUTPUT_DIR = Path(output_dir)
    if state.get("creator"):
        config.HTML_CREATOR_NAME = state["creator"]

    reviews = _read_json(workdir / REVIEWS_FILE)

    # ---- 第 1 步：校验并合并打标结果（幂等，每次 resume 都重跑） ----
    tagged_reviews = _merge_tagged_reviews(workdir, reviews, state["batch_size"])
    print(f"✅ 打标校验通过：共 {len(tagged_reviews)} 条评论打标完成")

    report_prompt_file = workdir / REPORT_PROMPT_FILE
    report_draft_file = workdir / REPORT_DRAFT_FILE

    # ---- 第 2 步：中间产出（生成报告 prompt） ----
    if not report_prompt_file.exists():
        personas, golden_samples, stats, anomaly_signals = _run_deterministic_analysis(
            tagged_reviews
        )
        print(f"✅ 确定性分析完成：{len(personas)} 个画像，平均评分 {stats.get('avg_rating', 0)}")
        if anomaly_signals:
            print(f"   ⚠️  检测到 {len(anomaly_signals)} 条异常信号: "
                  f"{', '.join(f'{s.signal_type}[{s.severity}]' for s in anomaly_signals)}")

        # 保存打标 CSV（路径存入 state，供跨日期 resume 对账）
        csv_path = pipeline_common.save_tagged_reviews_to_csv(tagged_reviews, asin)
        state["csv_path"] = str(csv_path)

        prompt = _build_report_prompt(
            tagged_reviews, personas, golden_samples, stats, anomaly_signals, asin
        )
        report_prompt_file.write_text(prompt, encoding="utf-8")

        state["phase"] = PHASE_AWAIT_REPORT
        _write_json(state_file, state)

        print("\n" + "=" * 70)
        print("📝 [Agent 自执行模式] 打标阶段完成！报告 prompt 已生成")
        print("=" * 70)
        print("\n📝 宿主 Agent 待办清单（第 2/3 步：撰写报告）：")
        print(f"   1. 读取 {report_prompt_file}")
        print("      严格按照 prompt 指令撰写完整 15 章洞察报告")
        print(f"   2. 把完整报告（Markdown）写到 {report_draft_file}")
        print("   3. 再次运行以下命令收尾：")
        print(f"      python3 main.py --resume {workdir}")
        print("=" * 70 + "\n")
        return

    # ---- 第 3 步：收尾（读报告草稿，产出最终输出包） ----
    if not report_draft_file.exists():
        # 幂等重入：prompt 已生成但草稿未写，重复打印待办指引
        print("\n" + "=" * 70)
        print(f"⏳ 当前状态: {state.get('phase', PHASE_AWAIT_REPORT)}（等待报告草稿）")
        print("=" * 70)
        print("\n📝 宿主 Agent 待办清单（第 2/3 步：撰写报告）：")
        print(f"   1. 读取 {report_prompt_file}")
        print("      严格按照 prompt 指令撰写完整 15 章洞察报告")
        print(f"   2. 把完整报告（Markdown）写到 {report_draft_file}")
        print("   3. 再次运行以下命令收尾：")
        print(f"      python3 main.py --resume {workdir}")
        print("=" * 70 + "\n")
        return

    _finalize(workdir, state_file, state, tagged_reviews)


def _finalize(workdir: Path, state_file: Path, state: dict, tagged_reviews: list) -> None:
    """收尾阶段：读报告草稿 → 纯 Python 后处理 → 输出最终 MD/CSV/HTML/飞书。

    报告后处理与 insights_generator.generate_insights 的 L184-215 完全同构：
    mermaid 兜底注入 + strategic_json 剥离提取（含异常信号侧通道注入，
    供 HTML 看板通过 insights_generator.get_last_strategic_data() 消费）。
    """
    asin = state["asin"]
    report_draft_file = workdir / REPORT_DRAFT_FILE

    # 中间产物从已合并的 tagged_reviews 确定性重算（纯 Python，成本零）
    personas, golden_samples, stats, anomaly_signals = _run_deterministic_analysis(
        tagged_reviews
    )

    report_text = report_draft_file.read_text(encoding="utf-8").strip()
    if not report_text:
        print(f"❌ 报告草稿为空: {report_draft_file}，请宿主 Agent 补写后重新 --resume")
        sys.exit(2)

    # 兜底：确保必需的 mermaid 图表存在（与 CLI 模式同构）
    report_text = _ensure_mermaid_charts(report_text, stats, personas)

    # 剥离 <strategic_json> 标签，提取数据供 HTML 看板使用（照抄 generate_insights）
    insights_generator._last_strategic_data = {}
    if report_text and "<strategic_json>" in report_text:
        import re as _re
        # 先提取 strategic_json 供 HTML 看板使用
        _match = _re.search(
            r'<strategic_json>\s*(\{.*?\})\s*</strategic_json>',
            report_text, _re.DOTALL,
        )
        if _match:
            try:
                insights_generator._last_strategic_data = json.loads(_match.group(1))
            except json.JSONDecodeError:
                pass
        # 再从报告中移除
        report_text = _re.sub(
            r'<strategic_json>.*?</strategic_json>', '', report_text, flags=_re.DOTALL
        ).strip()

    # Python 侧通道：将确定性异常检测结果直接注入 strategic_json
    # 不依赖 AI 回填 anomaly_cards 字段，看板从侧通道确定性渲染
    if anomaly_signals:
        try:
            anomaly_cards_serialized = []
            for sig in anomaly_signals:
                if hasattr(sig, "to_dict"):
                    anomaly_cards_serialized.append(sig.to_dict())
                elif isinstance(sig, dict):
                    anomaly_cards_serialized.append(sig)
            if anomaly_cards_serialized:
                insights_generator._last_strategic_data["anomaly_cards"] = anomaly_cards_serialized
        except Exception as exc:
            print(f"⚠️ 异常信号侧通道注入失败: {exc}")

    print(f"\n📦 [收尾] 报告草稿已确认（约 {len(report_text):,} 字），生成最终输出...")

    # 保存最终 Markdown
    md_path = config.get_md_path(asin)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # 输出阶段：打标 CSV + MD + HTML 看板 + 飞书同步（与 CLI 模式共享）
    pipeline_common.run_output_phase(
        tagged_reviews=tagged_reviews,
        stats=stats,
        personas=personas,
        golden_samples=golden_samples,
        insights_md=report_text,
        asin=asin,
        template_name=state.get("template"),
        feishu_sync=state.get("feishu_sync", False),
    )

    state["phase"] = PHASE_DONE
    _write_json(state_file, state)

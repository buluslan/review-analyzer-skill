# -*- coding: utf-8 -*-
"""agent_pipeline（Agent 自执行模式）hermetic 回归测试。

不联网、不调 CLI、不起子进程：用 tmp_path 造小 CSV（4 条评论，
batch_size=2），覆盖 prepare → resume(校验打标) → resume(中间产出)
→ resume(收尾) 完整状态机。template 传 none 跳过 HTML 看板。
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.data_loader import load_reviews_from_file
from src import agent_pipeline


ASIN = "B0TESTASIN1"

CSV_CONTENT = (
    "顾客名称,内容,打分,评论时间\n"
    "张三,这个键盘手感非常棒，家用办公都很合适，物流也很快,5,2026-03-01\n"
    "李四,质量太差了，按键经常不回弹，做工粗糙，想退货,1,2026-03-02\n"
    "王五,给女儿买的礼物，她很喜欢，续航也不错,4,2026-03-03\n"
    "赵六,价格偏贵，一般般吧，不太会复购,3,2026-03-04\n"
)


@pytest.fixture
def work_env(tmp_path, monkeypatch):
    """隔离环境：config 输出目录与署名都指向 tmp_path，返回 (tmp_path, reviews)。"""
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(config, "HTML_CREATOR_NAME", "测试署名")

    csv_path = tmp_path / f"reviews_{ASIN}.csv"
    csv_path.write_text(CSV_CONTENT, encoding="utf-8-sig")

    reviews, _ = load_reviews_from_file(str(csv_path))
    assert len(reviews) == 4
    return tmp_path, reviews


def _make_batch_result(batch):
    """按打标 prompt 要求的 JSON 数组格式伪造一批打标结果。"""
    results = []
    for r in batch:
        negative = float(r.get("rating", 0) or 0) <= 2
        results.append({
            "review_id": r["review_id"],
            "sentiment": "不推荐" if negative else "推荐",
            "info_score": 12,
            "tags": {
                "人群_性别": "男性",
                "人群_年龄段": "26-35",
                "场景_使用场景": "家用",
                "质量_做工": "粗糙" if negative else "精细",
                "体验_价格感知": "合理",
                "复购_复购意愿": "会复购",
                "情感_总体评价": "不推荐" if negative else "推荐",
            },
        })
    return json.dumps(results, ensure_ascii=False)


def _write_batch_results(workdir, reviews, batch_size=2):
    """为所有批次写伪造的打标结果 JSON（宿主 Agent 的角色）。"""
    batches = [reviews[i:i + batch_size] for i in range(0, len(reviews), batch_size)]
    result_files = []
    for i, batch in enumerate(batches, 1):
        result_file = workdir / "tagging" / f"batch_{i:03d}.json"
        result_file.write_text(_make_batch_result(batch), encoding="utf-8")
        result_files.append(result_file)
    return result_files


REPORT_DRAFT = "\n".join(
    ["# 测试报告", ""]
    + [f"## {cn}、测试章节 {cn}" for cn in
       ["一", "二", "三", "四", "五（主要痛点与负面归因）", "六", "七", "八",
        "九", "十", "十一", "十二", "十三", "十四", "十五"]]
    + ["", "正文内容占位。", '<strategic_json>{"strategy": {"goal": "测试"}}</strategic_json>']
)


# ==================== prepare ====================


def test_prepare_creates_workdir_and_prompts(work_env):
    """prepare 生成 state.json / reviews.json / 各批次 prompt，数量正确。"""
    tmp_path, reviews = work_env

    workdir = agent_pipeline.prepare(
        reviews=reviews, asin=ASIN, batch_size=2, template="none",
    )

    assert workdir == tmp_path / f"agent_work_{ASIN}"
    assert (workdir / "state.json").exists()
    assert (workdir / "reviews.json").exists()

    state = json.loads((workdir / "state.json").read_text(encoding="utf-8"))
    assert state["asin"] == ASIN
    assert state["batch_size"] == 2
    assert state["template"] == "none"
    assert state["creator"] == "测试署名"
    assert state["feishu_sync"] is False
    assert state["total_reviews"] == 4
    assert state["phase"] == "await_tagging"

    # reviews.json 保存完整 dict（含 _original_data），供 resume 回填
    saved = json.loads((workdir / "reviews.json").read_text(encoding="utf-8"))
    assert len(saved) == 4
    assert "_original_data" in saved[0]

    # 4 条评论 / batch_size=2 → 2 个批次 prompt，三位数编号
    prompt_files = sorted((workdir / "tagging").glob("batch_*_prompt.md"))
    assert [p.name for p in prompt_files] == ["batch_001_prompt.md", "batch_002_prompt.md"]
    # prompt 内容来自 build_tagging_prompt，包含评论数据
    assert "review_id" in prompt_files[0].read_text(encoding="utf-8")


# ==================== resume：校验打标 ====================


def test_resume_missing_results_exits_2(work_env, capsys):
    """批次结果缺失时列出缺失文件并退出码 2。"""
    tmp_path, reviews = work_env
    workdir = agent_pipeline.prepare(reviews=reviews, asin=ASIN, batch_size=2)

    with pytest.raises(SystemExit) as exc_info:
        agent_pipeline.resume(str(workdir))
    assert exc_info.value.code == 2

    out = capsys.readouterr().out
    assert "batch_001.json" in out
    assert "batch_002.json" in out


def test_resume_invalid_result_json_exits_2(work_env, capsys):
    """批次结果存在但解析失败时，列出批次让 Agent 重写并退出码 2。"""
    tmp_path, reviews = work_env
    workdir = agent_pipeline.prepare(reviews=reviews, asin=ASIN, batch_size=2)

    (workdir / "tagging" / "batch_001.json").write_text(
        _make_batch_result(reviews[:2]), encoding="utf-8")
    # 第二批写一个非法 JSON（不是数组开头）
    (workdir / "tagging" / "batch_002.json").write_text(
        "这不是一个 JSON 数组", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        agent_pipeline.resume(str(workdir))
    assert exc_info.value.code == 2

    out = capsys.readouterr().out
    assert "batch_002.json" in out


# ==================== resume：中间产出 ====================


def test_resume_generates_report_prompt_and_csv(work_env):
    """打标齐备后 resume 生成 report_prompt.md 与打标 CSV，phase 推进。"""
    tmp_path, reviews = work_env
    workdir = agent_pipeline.prepare(reviews=reviews, asin=ASIN, batch_size=2)
    _write_batch_results(workdir, reviews, batch_size=2)

    agent_pipeline.resume(str(workdir))  # 不应退出

    report_prompt = workdir / "report_prompt.md"
    assert report_prompt.exists()
    prompt_text = report_prompt.read_text(encoding="utf-8")
    assert ASIN in prompt_text
    assert len(prompt_text) > 1000  # 15 章 prompt 体量检查

    state = json.loads((workdir / "state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "await_report"
    # 打标 CSV 已保存且路径存入 state
    assert state.get("csv_path")
    assert Path(state["csv_path"]).exists()
    # 打标结果已回填（负面评论 → 不推荐情感）
    import pandas as pd
    df = pd.read_csv(state["csv_path"], encoding="utf-8-sig")
    assert "情感_总体评价" in df.columns
    assert "不推荐" in set(df["情感_总体评价"])


def test_resume_await_report_is_idempotent(work_env, capsys):
    """report_prompt 已生成但草稿未写时重复 resume，重复打印待办不报错。"""
    tmp_path, reviews = work_env
    workdir = agent_pipeline.prepare(reviews=reviews, asin=ASIN, batch_size=2)
    _write_batch_results(workdir, reviews, batch_size=2)
    agent_pipeline.resume(str(workdir))

    # 第二次 resume：无草稿 → 幂等重入，仅提示待办
    agent_pipeline.resume(str(workdir))
    out = capsys.readouterr().out
    assert "report_draft.md" in out

    state = json.loads((workdir / "state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "await_report"


# ==================== resume：收尾 ====================


def test_resume_finalize_produces_outputs(work_env):
    """写 report_draft.md 后 resume 收尾，产出最终 MD（含后处理）。"""
    tmp_path, reviews = work_env
    workdir = agent_pipeline.prepare(reviews=reviews, asin=ASIN, batch_size=2)
    _write_batch_results(workdir, reviews, batch_size=2)
    agent_pipeline.resume(str(workdir))

    (workdir / "report_draft.md").write_text(REPORT_DRAFT, encoding="utf-8")
    agent_pipeline.resume(str(workdir))  # 收尾，不应退出

    # 最终 MD 已生成（OutputManager 写到 config.OUTPUT_DIR）
    final_md = tmp_path / f"分析洞察报告_{ASIN}.md"
    assert final_md.exists()
    content = final_md.read_text(encoding="utf-8")
    assert "测试报告" in content
    # strategic_json 已剥离（提取供看板侧通道）
    assert "<strategic_json>" not in content
    # mermaid 兜底：第五章标题存在时自动注入
    assert "```mermaid" in content

    # 打标 CSV 存在
    csv_files = list(tmp_path.rglob(f"评论采集及打标数据_{ASIN}.csv"))
    assert csv_files

    # HTML 看板跳过（template=none）
    assert not list(tmp_path.rglob(f"可视化洞察报告_{ASIN}.html"))

    # 状态机推进到 done
    state = json.loads((workdir / "state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "done"


def test_resume_restores_output_dir_across_process(work_env):
    """resume 是独立进程：config 回默认值后，输出目录仍从 state 快照恢复。

    回归点：resume 若不恢复 --output-dir，产物会落到默认 ./output
    而不是 prepare 时指定的目录。
    """
    tmp_path, reviews = work_env
    workdir = agent_pipeline.prepare(reviews=reviews, asin=ASIN, batch_size=2)
    _write_batch_results(workdir, reviews, batch_size=2)
    agent_pipeline.resume(str(workdir))
    (workdir / "report_draft.md").write_text(REPORT_DRAFT, encoding="utf-8")

    # 模拟新进程：config.OUTPUT_DIR 回到别的默认目录
    config.OUTPUT_DIR = tmp_path / "elsewhere"

    agent_pipeline.resume(str(workdir))

    # 产物落在 prepare 时的输出目录（state 快照），而不是 elsewhere
    assert (tmp_path / f"分析洞察报告_{ASIN}.md").exists()
    assert not (tmp_path / "elsewhere" / f"分析洞察报告_{ASIN}.md").exists()

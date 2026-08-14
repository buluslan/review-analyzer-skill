# -*- coding: utf-8 -*-
"""review_analyzer._parse_batch_response 解析容错测试。

覆盖：纯 JSON 数组、markdown 代码块包裹、代码块前后带说明文字、
无代码块但前后带文字、截断 JSON 修复、完全无 JSON 抛 ValueError、
review_id 缺失/未知时的合并回退逻辑。
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.review_analyzer import _parse_batch_response  # noqa: E402


def make_batch():
    """构造原始批次（2 条），供合并逻辑配对。"""
    return [
        {"review_id": "r1", "body": "Solid build quality.", "rating": 5},
        {"review_id": "r2", "body": "Broke after a week.", "rating": 1},
    ]


def make_results(include_r2=True):
    r = [{
        "review_id": "r1",
        "sentiment": "推荐",
        "info_score": 8,
        "tags": {"质量_做工": "好"},
    }]
    if include_r2:
        r.append({
            "review_id": "r2",
            "sentiment": "不推荐",
            "info_score": 3,
            "tags": {"质量_耐用性": "易坏"},
        })
    return r


def by_id(results, rid):
    for r in results:
        if r["review_id"] == rid:
            return r
    return None


# ==================== 正常解析路径 ====================


def test_pure_json_array():
    results = _parse_batch_response(json.dumps(make_results(), ensure_ascii=False),
                                    make_batch())
    assert len(results) == 2
    merged = by_id(results, "r1")
    assert merged["sentiment"] == "推荐"
    assert merged["tags"] == {"质量_做工": "好"}
    # 原始字段在合并结果中保留
    assert merged["body"] == "Solid build quality."
    assert merged["rating"] == 5
    assert by_id(results, "r2")["sentiment"] == "不推荐"


def test_markdown_json_code_block():
    """```json ... ``` 包裹的响应能正确提取代码块内 JSON。"""
    payload = json.dumps(make_results(), ensure_ascii=False)
    response = f"```json\n{payload}\n```"
    results = _parse_batch_response(response, make_batch())
    assert len(results) == 2
    assert by_id(results, "r1")["tags"] == {"质量_做工": "好"}


def test_markdown_bare_code_block():
    """无语言标注的 ``` ... ``` 代码块同样支持。"""
    payload = json.dumps(make_results(), ensure_ascii=False)
    response = f"```\n{payload}\n```"
    results = _parse_batch_response(response, make_batch())
    assert len(results) == 2


def test_code_block_with_surrounding_prose():
    """代码块前后带模型说明文字：优先提取代码块内 JSON。"""
    payload = json.dumps(make_results(), ensure_ascii=False)
    response = f"以下是打标结果：\n```json\n{payload}\n```\n以上共 2 条。"
    results = _parse_batch_response(response, make_batch())
    assert len(results) == 2
    assert by_id(results, "r1")["sentiment"] == "推荐"


def test_json_with_surrounding_prose_no_code_block():
    """无代码块但 JSON 前后有说明文字：按方括号配对截取数组。"""
    payload = json.dumps(make_results(), ensure_ascii=False)
    response = f"打标完成，结果如下：\n{payload}\n如需调整请告知。"
    results = _parse_batch_response(response, make_batch())
    assert len(results) == 2
    assert by_id(results, "r2")["tags"] == {"质量_耐用性": "易坏"}


# ==================== 截断修复路径 ====================


def test_truncated_json_repaired():
    """响应被截断（无闭合 ]）：截到最后一个完整对象并补 ]。

    r1 完整、r2 残缺 -> r1 正常合并，r2 走未处理回退（sentiment=解析失败）。
    """
    response = (
        '[{"review_id": "r1", "sentiment": "推荐", "info_score": 8, "tags": {}}, '
        '{"review_id": "r2", "sentim'
    )
    results = _parse_batch_response(response, make_batch())
    assert len(results) == 2
    merged = by_id(results, "r1")
    assert merged["sentiment"] == "推荐"
    fallback = by_id(results, "r2")
    assert fallback["sentiment"] == "解析失败"
    assert fallback["info_score"] == 0
    assert fallback["tags"] == {}
    assert fallback["body"] == "Broke after a week."  # 原始数据保留


def test_truncated_json_without_complete_object_raises():
    """截断且没有任何完整对象 -> ValueError。"""
    response = '[{"review_id": "r1", "sentim'
    with pytest.raises(ValueError):
        _parse_batch_response(response, make_batch())


# ==================== 无 JSON / 格式错误 ====================


def test_no_json_raises_value_error():
    """完全没有 '[' -> ValueError。"""
    with pytest.raises(ValueError, match="未找到 JSON 数组"):
        _parse_batch_response("抱歉，我无法处理这批评论数据。", make_batch())


# ==================== 合并回退逻辑 ====================


def test_missing_review_id_skipped_with_fallback():
    """结果项缺 review_id 被跳过，对应原评论回退为未打标。"""
    response = json.dumps([{"sentiment": "推荐", "tags": {}}])
    results = _parse_batch_response(response, make_batch())
    assert len(results) == 2
    assert all(r["sentiment"] == "解析失败" for r in results)


def test_unknown_review_id_skipped():
    """响应中的未知 review_id 被跳过，不进入合并结果。"""
    response = json.dumps([
        {"review_id": "r1", "sentiment": "推荐", "info_score": 5, "tags": {}},
        {"review_id": "ghost", "sentiment": "推荐", "info_score": 5, "tags": {}},
    ])
    results = _parse_batch_response(response, make_batch())
    ids = {r["review_id"] for r in results}
    assert "ghost" not in ids
    # r2 未被处理 -> 回退追加
    assert by_id(results, "r2")["sentiment"] == "解析失败"


def test_partial_results_completed_with_fallback():
    """只返回 r1 时，r2 自动补齐为未打标结果，保证返回条数与批次一致。"""
    response = json.dumps(make_results(include_r2=False), ensure_ascii=False)
    results = _parse_batch_response(response, make_batch())
    assert len(results) == 2
    assert by_id(results, "r1")["sentiment"] == "推荐"
    assert by_id(results, "r2")["sentiment"] == "解析失败"


def test_non_array_json_raises_value_error():
    """纯 JSON 对象（无 '['）-> ValueError（未找到数组起始符号）。"""
    response = '{"review_id": "r1"}'
    with pytest.raises(ValueError, match="未找到 JSON 数组"):
        _parse_batch_response(response, make_batch())

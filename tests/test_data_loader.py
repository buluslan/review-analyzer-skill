# -*- coding: utf-8 -*-
"""data_loader.load_reviews_from_file 列名嗅探回归测试。

重点回归：body_keywords 曾含泛词 'review'，会把 review_id 列误判为正文列；
修复后 body_keywords 为精确词（review_body/review_content/review_text/
内容/评价/正文/body/text/content），review_id 不再命中。
"""

import sys
from pathlib import Path

import pandas as pd  # noqa: F401  (确认依赖可用)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_reviews_from_file  # noqa: E402


def write_csv(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8-sig")
    return str(p)


# ==================== 正文列嗅探 ====================


def test_body_column_not_confused_by_review_id(tmp_path):
    """review_id/review_title/review_body 并存时，正文列必须是 review_body。

    回归点：旧实现 body_keywords 含泛词 'review'，review_id 会先于
    review_body 被命中，导致正文取到 ID。修复后精确词不误判。
    """
    csv_path = write_csv(tmp_path, "en.csv",
        "review_id,review_title,review_body,rating\n"
        "1001,Great product,This keyboard feels solid and types smoothly.,5\n"
        "1002,Broke fast,It stopped working after only two weeks of use.,1\n")
    reviews, df = load_reviews_from_file(csv_path)

    assert len(reviews) == 2
    assert reviews[0]["body"] == "This keyboard feels solid and types smoothly."
    assert reviews[1]["body"] == "It stopped working after only two weeks of use."
    assert reviews[0]["review_id"] != "1001"  # review_id 是重新生成的 uuid
    assert "review_title" in df.columns


def test_chinese_column_names(tmp_path):
    """中文列名（内容/打分）能被正确嗅探。"""
    csv_path = write_csv(tmp_path, "cn.csv",
        "顾客名称,内容,打分,评论时间\n"
        "张三,这个键盘手感非常棒，物流也很快,5,2026-03-01\n"
        "李四,质量太差了，按键经常不回弹,1,2026-03-02\n")
    reviews, _ = load_reviews_from_file(csv_path)

    assert len(reviews) == 2
    assert reviews[0]["body"] == "这个键盘手感非常棒，物流也很快"
    assert reviews[0]["rating"] == 5.0
    assert reviews[1]["rating"] == 1.0
    assert reviews[0]["date"] == "2026-03-01"


def test_review_title_not_picked_as_body(tmp_path):
    """review_title 列（短标题）不能被当作正文列。"""
    csv_path = write_csv(tmp_path, "title.csv",
        "review_title,review_content\n"
        "Nice,A surprisingly sturdy little adapter for the price.\n")
    reviews, _ = load_reviews_from_file(csv_path)
    assert reviews[0]["body"] == "A surprisingly sturdy little adapter for the price."


# ==================== 缺列默认行为 ====================


def test_missing_rating_column_defaults_to_zero(tmp_path):
    """无评分列时 rating 默认 0.0，不抛异常。"""
    csv_path = write_csv(tmp_path, "norating.csv",
        "review_body\n"
        "Works exactly as described and arrived quickly.\n"
        "Batteries died within a month of light usage.\n")
    reviews, _ = load_reviews_from_file(csv_path)
    assert len(reviews) == 2
    assert all(r["rating"] == 0.0 for r in reviews)


def test_missing_body_column_raises(tmp_path):
    """找不到任何正文列时抛异常。"""
    csv_path = write_csv(tmp_path, "nobody.csv",
        "review_id,rating\n1,5\n2,4\n")
    try:
        load_reviews_from_file(csv_path)
    except Exception:
        return
    raise AssertionError("缺少正文列应抛出异常")


# ==================== 数据清洗 ====================


def test_short_and_nan_bodies_dropped(tmp_path):
    """NaN 正文和长度<3 的正文被清洗跳过。"""
    csv_path = write_csv(tmp_path, "dirty.csv",
        "review_body,rating\n"
        "This one is a perfectly valid review body.,5\n"
        ",5\n"
        "ok,4\n")
    reviews, _ = load_reviews_from_file(csv_path)
    assert len(reviews) == 1
    assert reviews[0]["body"] == "This one is a perfectly valid review body."


def test_non_numeric_rating_falls_back_to_zero(tmp_path):
    """评分列值不可解析时降级为 0.0。"""
    csv_path = write_csv(tmp_path, "badrating.csv",
        "review_body,rating\n"
        "Great value overall and would buy again.,five\n")
    reviews, _ = load_reviews_from_file(csv_path)
    assert reviews[0]["rating"] == 0.0

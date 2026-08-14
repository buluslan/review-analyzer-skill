"""
流水线共享函数模块 V2.1

抽取 main.py 中被 cli / agent 两种 LLM 执行模式共用的确定性工序：
- 打标结果 CSV 保存
- ASIN 提取
- Phase 4 输出阶段（MD + HTML 看板 + 飞书同步）

单一真理源：main.py 与 agent_pipeline.py 均 import 使用，不复制代码。
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import config


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


def run_output_phase(
    tagged_reviews: list,
    stats: dict,
    personas: list,
    golden_samples: list,
    insights_md: str,
    asin: str,
    template_name,
    feishu_sync: bool,
) -> dict:
    """Phase 4 输出阶段：保存打标 CSV + 生成 MD/HTML 看板 + 飞书同步。

    从 main.py 原 Phase 4 输出块原样抽取（V2.1 共享给 agent 模式收尾），
    打印逻辑保留，行为与原 CLI 模式完全一致。

    Args:
        tagged_reviews: 已打标评论列表
        stats: 统计摘要，来自 calculate_stats_summary()
        personas: 用户画像列表，来自 analyze_user_personas()
        golden_samples: 黄金样本列表，来自 analyze_user_personas()
        insights_md: 洞察报告 Markdown 正文
        asin: 产品 ASIN
        template_name: 可视化看板模板名称（"none" 或 None 跳过 HTML）
        feishu_sync: 是否同步到飞书

    Returns:
        {
            "output_results": generate_outputs 的完整结果,
            "csv_path": 打标 CSV 路径,
            "md_path": 洞察报告 MD 路径,
            "html_path": HTML 看板路径（未生成时为空字符串）,
            "template_name": 归一化后的模板名称（跳过时为 None）,
        }
    """
    # 保存 CSV（先于输出包，最终打印需要引用文件名）
    csv_path = save_tagged_reviews_to_csv(tagged_reviews, asin)

    print(f"📦 [Phase 4/4] 生成完整输出包...")
    from src.output_manager import generate_outputs

    # 选择模板（none 表示跳过 HTML 生成）
    if template_name is not None and str(template_name).lower() == "none":
        template_name = None  # 跳过 HTML 看板
    elif template_name:
        # 如果模板不存在，使用默认
        try:
            from src.template_engine import list_templates as _lt
            available = [t["name"] for t in _lt()]
            if template_name not in available:
                print(f"   ⚠️ 模板 '{template_name}' 不存在，使用默认模板")
                template_name = available[0] if available else "premium-gold"
        except Exception:
            pass

    # 构建统计摘要
    summary = {
        "total": len(tagged_reviews),
        "tagged": stats["tagged"],
        "persona_count": len(personas),
        "avg_rating": stats.get("avg_rating", 0),
        "sentiment": stats.get("sentiment", {}),
        "top_tags": stats.get("top_tags", {})
    }

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
        "dimensional_stats": stats.get("dimensional_stats", {}),
        "personas": [{"name": p.get("name", ""), "count": p.get("count", 0), "tags": p.get("tags", {})} for p in personas],
        "golden_samples": golden_samples,
        "insights_md": insights_md,
        "statistics": stats,
    }

    output_config = {
        "template_name": template_name,
        "sync_feishu": feishu_sync,
        "output_dir": str(config.OUTPUT_DIR),
        "asin": asin,
        "creator": config.HTML_CREATOR_NAME,
    }

    output_results = generate_outputs(analysis_data_for_output, output_config)

    # 飞书同步结果
    feishu_result = output_results.get("feishu_result", {})
    if feishu_sync:
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
    final_md = output_results.get("md_path", "")
    final_html = output_results.get("html_path", "")

    print("\n" + "✨" * 30)
    print("🎉 分析任务圆满完成！")
    print(f"  - 洞察报告: {Path(final_md).name if final_md else '未生成'}")
    print(f"  - 结构数据: {csv_path.name}")
    if final_html:
        print(f"  - 可视化看板: {Path(final_html).name} (模板: {template_name})")
    else:
        print(f"  - 可视化看板: 已跳过")
    if feishu_sync and feishu_result and feishu_result.get("doc_url"):
        print(f"  - 飞书文档: {feishu_result['doc_url']}")
        wb_count = feishu_result.get("whiteboard_count", 0)
        if wb_count > 0:
            print(f"  - 白板图表: {wb_count} 个")
    print("✨" * 30 + "\n")

    return {
        "output_results": output_results,
        "csv_path": csv_path,
        "md_path": final_md,
        "html_path": final_html,
        "template_name": template_name,
    }

"""
AI 分析引擎模块 V1.0 - CLI 原生版

重大变更：彻底移除第三方 API 依赖
- 移除 google.generativeai (Gemini API)
- 移除 Anthropic API 直接调用
- 改用 Python subprocess 调用宿主系统的 Claude Code CLI (claude -p)
- 所有 AI 推理通过 CLI 进行，使用您的 Claude 配额
"""

import json
import logging
import os
import shutil
import subprocess
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from src.config import config
from src.prompts.templates import get_tagging_prompt_batch

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_all(reviews: List[Dict], batch_size: int = 30) -> List[Dict]:
    """使用 Claude Code CLI 并发分析所有评论

    将评论按批次并发处理，每批通过 subprocess 调用 claude -p 进行批量打标。
    支持进度显示和错误处理。

    Args:
        reviews: 原始评论列表，每条评论需包含:
            - review_id: 评论唯一标识
            - body: 评论内容
            - rating: 评分星级
        batch_size: 每批处理数量，默认30，推荐范围20-50

    Returns:
        添加了以下字段的评论列表:
            - sentiment: 情感倾向 (强烈推荐/推荐/中立/不推荐/强烈不推荐)
            - info_score: 信息密度评分 (1-20)
            - tags: 22维度标签字典

    Raises:
        ValueError: 当 batch_size 不在有效范围内时

    Example:
        >>> reviews = [{"review_id": "1", "body": "...", "rating": 5}]
        >>> results = analyze_all(reviews, batch_size=30)
        >>> print(results[0]["sentiment"])
        '强烈推荐'
    """
    # 验证参数
    if not 20 <= batch_size <= 50:
        raise ValueError(f"batch_size 必须在 20-50 之间，当前值: {batch_size}")

    if not reviews:
        logger.warning("输入评论列表为空")
        return []

    total_reviews = len(reviews)
    logger.info(f"开始分析 {total_reviews} 条评论，批次大小: {batch_size}")
    logger.info(f"使用引擎: Claude Code CLI ({config.CLAUDE_CLI_CMD})")

    # 分批处理
    batches = _chunk_reviews(reviews, batch_size)
    total_batches = len(batches)
    logger.info(f"共分为 {total_batches} 个批次")

    # 并发处理所有批次
    results = []
    failed_batches = []
    batch_times = {}  # 记录每个批次的处理时间
    batch_start_times = {}  # 记录每个批次的开始时间
    completed_count = 0  # 记录完成的批次数量（按完成顺序）

    # 尝试导入 tqdm 用于进度显示
    try:
        from tqdm import tqdm
        progress_bar = tqdm(total=total_reviews, desc="打标进度", unit="条", disable=False)
        logger.info(f"✅ 进度条已创建，总评论数: {total_reviews}")
    except ImportError:
        progress_bar = None
        logger.warning("⚠️  未安装 tqdm，将使用文本日志显示进度")

    # 显示启动信息
    logger.info(f"🚀 启动并发处理: {total_batches}个批次，每批{batch_size}条评论")
    logger.info(f"🔧 并发工作线程数: {config.MAX_CONCURRENT_AGENTS}")
    logger.info(f"⏱️  CLI超时设置: {config.CLI_TIMEOUT}秒/批次")
    logger.info(f"🕐 总体开始时间: {time.strftime('%H:%M:%S')}")

    with ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_AGENTS) as executor:
        # 提交所有批次任务
        future_to_batch = {}
        logger.info(f"📤 提交{total_batches}个批次任务到线程池...")

        for i, batch in enumerate(batches):
            batch_start_times[i] = time.time()  # 记录开始时间
            future = executor.submit(analyze_batch, batch, i)
            future_to_batch[future] = i
            logger.info(f"   ✓ 批次 {i + 1}/{total_batches} 已提交 (包含{len(batch)}条评论)")

        logger.info(f"✅ 所有批次已提交，等待处理结果...")
        logger.info(f"💡 提示: 如果长时间无进度更新，请检查 CLI 是否可用")

        # 收集结果
        for future in as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            completed_count += 1

            # 计算实际处理耗时
            elapsed = time.time() - batch_start_times[batch_idx]

            # 显示批次开始处理
            logger.info(f"⏳ 批次 {batch_idx + 1}/{total_batches} 正在处理...")

            try:
                batch_results = future.result()
                results.extend(batch_results)

                if progress_bar:
                    # 更新进度：增加本批次处理的评论数
                    progress_bar.update(len(batch_results))
                    progress_bar.set_postfix({
                        "批次": f"{len(results) // batch_size + 1}/{total_batches}",
                        "已完成": f"{len(results)}/{total_reviews}",
                        "进度": f"{len(results)/total_reviews*100:.1f}%"
                    })
                    # 立即刷新进度条显示
                    progress_bar.refresh()

                logger.info(
                    f"✅ 批次 {batch_idx + 1}/{total_batches} 完成 "
                    f"({len(results)}/{total_reviews}, {len(results)/total_reviews*100:.1f}%, "
                    f"耗时: {elapsed:.1f}秒, 完成序列: {completed_count})"
                )

            except Exception as e:
                failed_batches.append(batch_idx)
                logger.error(
                    f"❌ 批次 {batch_idx + 1}/{total_batches} 失败: {str(e)}",
                    exc_info=True
                )

                if progress_bar:
                    # 失败批次也需要更新进度（使用批次大小）
                    batch_size_actual = len(batches[batch_idx]) if batch_idx < len(batches) else 0
                    progress_bar.update(batch_size_actual)
                    progress_bar.set_postfix({
                        "批次": f"{len(results) // batch_size + 1}/{total_batches}",
                        "已完成": f"{len(results)}/{total_reviews}",
                        "进度": f"{len(results)/total_reviews*100:.1f}%"
                    })
                    progress_bar.refresh()

    if progress_bar:
        progress_bar.close()

    # 处理失败批次：重试机制
    if failed_batches:
        logger.warning(f"有 {len(failed_batches)} 个批次失败，尝试重试...")
        retry_results = _retry_failed_batches(
            [batches[i] for i in failed_batches],
            failed_batches
        )
        results.extend(retry_results)

    # 记录最终统计
    success_count = len(results)
    failed_count = total_reviews - success_count

    # 计算总体耗时
    total_time = time.time() - batch_start_times[0] if batch_start_times else 0
    avg_time_per_batch = sum(batch_times.values()) / len(batch_times) if batch_times else 0
    avg_time_per_review = total_time / total_reviews if total_reviews > 0 else 0

    # 输出总体进度汇总
    logger.info("=" * 60)
    logger.info("📊 评论打标完成统计")
    logger.info(f"   总评论数: {total_reviews} 条")
    logger.info(f"   总批次: {total_batches} 批")
    logger.info(f"   总耗时: {total_time/60:.1f}分钟 ({total_time:.0f}秒)")
    logger.info(f"   平均每批: {avg_time_per_batch:.1f}秒")
    logger.info(f"   平均每条: {avg_time_per_review:.1f}秒")
    logger.info(f"   成功: {success_count} 条, 失败: {failed_count} 条")
    logger.info(f"   成功率: {success_count/total_reviews*100:.1f}% ({success_count}/{total_reviews})")
    logger.info("=" * 60)

    return results


def analyze_batch(batch: List[Dict], batch_idx: int = -1) -> List[Dict]:
    """分析单批评论

    通过 subprocess 调用 claude -p 对一批评论进行批量打标，包含重试机制。

    Args:
        batch: 评论批次，包含20-50条评论，每条需包含:
            - review_id: 评论唯一标识
            - body: 评论内容
            - rating: 评分星级
        batch_idx: 批次索引（用于日志记录）

    Returns:
        打标结果列表，每条包含:
            - review_id: 原始评论ID
            - sentiment: 情感倾向
            - info_score: 信息密度评分
            - tags: 22维度标签

    Raises:
        RuntimeError: 当 CLI 调用失败且重试次数用尽时
        ValueError: 当响应格式不正确时

    Example:
        >>> batch = reviews[0:30]
        >>> results = analyze_batch(batch)
        >>> print(len(results))
        30
    """
    max_retries = 3
    last_error = None

    # 记录线程信息
    thread_id = threading.current_thread().name
    batch_display = batch_idx + 1 if batch_idx >= 0 else "?"

    logger.info(f"🔵 批次 {batch_display} 由线程 '{thread_id}' 开始处理 (包含 {len(batch)} 条评论)")
    logger.debug(f"📦 开始处理批次，包含 {len(batch)} 条评论")

    for attempt in range(max_retries):
        try:
            # 构造提示词
            logger.debug(f"🔨 构造提示词 (尝试 {attempt + 1}/{max_retries})...")
            prompt = get_tagging_prompt_batch(batch)

            # 🔥 核心：调用 Claude Code CLI
            logger.info(f"📞 调用 Claude Code CLI (尝试 {attempt + 1}/{max_retries})...")
            logger.debug(f"   - 提示词长度: {len(prompt)} 字符")
            logger.debug(f"   - 超时设置: {config.CLI_TIMEOUT} 秒")

            response_text = _call_claude_cli(prompt)

            logger.info(f"✅ CLI 调用成功，响应长度: {len(response_text)} 字符")

            # 解析响应
            logger.debug(f"🔍 解析 JSON 响应...")
            results = _parse_batch_response(
                response_text,
                batch
            )

            logger.info(
                f"✅ 批次分析成功: {len(results)}/{len(batch)} 条 "
                f"(尝试 {attempt + 1}/{max_retries}, 线程: {thread_id})"
            )

            return results

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                f"⚠️  JSON 解析失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            )

            # 最后一次尝试失败时，返回部分解析结果
            if attempt == max_retries - 1:
                logger.error("❌ JSON 解析失败，返回原始评论（未打标）")
                return _get_failed_batch_results(batch, "JSON_PARSE_ERROR")

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            last_error = e
            logger.warning(
                f"⚠️  CLI 调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            )

            # 最后一次尝试失败
            if attempt == max_retries - 1:
                logger.error("❌ CLI 调用失败，返回原始评论（未打标）")
                return _get_failed_batch_results(batch, str(e))

        except Exception as e:
            last_error = e
            logger.warning(
                f"⚠️  未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            )

            if attempt == max_retries - 1:
                logger.error("❌ 未知错误，返回原始评论（未打标）")
                return _get_failed_batch_results(batch, str(e))

    # 理论上不会到达这里
    return _get_failed_batch_results(batch, str(last_error))


# ==================== 私有辅助函数 ====================

def _call_claude_cli(prompt: str, max_retries: int = 3) -> str:
    """调用 Claude Code CLI 进行 AI 推理

    这是 V1.0 的核心函数，通过 subprocess 调用宿主系统的 claude -p 命令。
    V1.0 热修复: 使用绝对路径避免 shell alias 干扰

    Args:
        prompt: 提示词
        max_retries: 最大重试次数（默认3次）

    Returns:
        CLI 返回的文本内容

    Raises:
        subprocess.TimeoutExpired: 超时
        subprocess.SubprocessError: 子进程错误
        json.JSONDecodeError: JSON 解析失败
    """
    # 🔥 热修复: 使用绝对路径，避免 shell alias 干扰
    claude_path = shutil.which(config.CLAUDE_CLI_CMD)
    if not claude_path:
        raise RuntimeError(
            f"❌ 找不到 Claude CLI: {config.CLAUDE_CLI_CMD}\n"
            f"请确保已安装 Claude Code 并正确配置 PATH"
        )

    logger.info(f"🔧 使用 Claude CLI 绝对路径: {claude_path}")

    for attempt in range(max_retries):
        try:
            # 构造命令：使用绝对路径和长格式参数
            cmd = [
                claude_path,  # 使用绝对路径而不是 "claude" 字符串
                "--print",  # 使用长格式 --print 而不是 -p
                "--dangerously-skip-permissions",
                prompt
            ]

            logger.debug(f"调用 CLI: {claude_path} --print <prompt长度={len(prompt)}>")

            # 执行命令，设置超时，传递环境变量
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.CLI_TIMEOUT,
                check=True,
                env={**os.environ, 'PATH': os.environ.get('PATH', '')}  # 传递环境变量
            )

            # 检查返回码
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "未知错误"
                logger.error(f"🔴 Claude CLI 失败 (返回码 {result.returncode})")
                logger.error(f"🔴 错误信息: {error_msg}")
                logger.error(f"🔴 命令: {' '.join(cmd)}")
                raise subprocess.SubprocessError(
                    f"Claude CLI 返回非零状态码 ({result.returncode}): {error_msg}"
                )

            # 返回 stdout
            response_text = result.stdout.strip()
            logger.debug(f"CLI 返回内容长度: {len(response_text)}")

            if not response_text:
                raise subprocess.SubprocessError("Claude CLI 返回空内容")

            return response_text

        except subprocess.TimeoutExpired:
            timeout_seconds = config.CLI_TIMEOUT
            logger.warning(
                f"⏰ CLI 调用超时 (尝试 {attempt + 1}/{max_retries}, "
                f"等待超过 {timeout_seconds} 秒)"
            )
            logger.warning(f"💡 可能原因:")
            logger.warning(f"   1. CLI 正在处理复杂任务，需要更长时间")
            logger.warning(f"   2. 网络延迟或 API 响应慢")
            logger.warning(f"   3. CLI 进程卡住或崩溃")
            logger.warning(f"💡 建议:")
            logger.warning(f"   - 检查 CLI 是否可用: claude --version")
            logger.warning(f"   - 增加超时时间: 修改 config.CLI_TIMEOUT")
            logger.warning(f"   - 减少批次大小: 降低单批次评论数")
            if attempt == max_retries - 1:
                raise

        except subprocess.CalledProcessError as e:
            logger.warning(f"❌ CLI 调用失败 (尝试 {attempt + 1}/{max_retries}): {e.stderr}")
            if attempt == max_retries - 1:
                raise subprocess.SubprocessError(f"Claude CLI 执行失败: {e.stderr}")

        except Exception as e:
            logger.warning(f"⚠️  未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise

    raise RuntimeError("CLI 调用失败：超过最大重试次数")


def _chunk_reviews(reviews: List[Dict], batch_size: int) -> List[List[Dict]]:
    """将评论列表按批次大小分组

    Args:
        reviews: 评论列表
        batch_size: 批次大小

    Returns:
        二维列表，每个子列表包含一个批次的评论
    """
    batches = []
    for i in range(0, len(reviews), batch_size):
        batches.append(reviews[i:i + batch_size])
    return batches


def _parse_batch_response(
    response_text: str,
    original_batch: List[Dict]
) -> List[Dict]:
    """解析批量响应

    从 Claude CLI 响应中提取 JSON 结果，并与原始评论合并。

    Args:
        response_text: CLI 返回的文本响应
        original_batch: 原始评论批次

    Returns:
        合并后的评论列表（包含打标结果）

    Raises:
        json.JSONDecodeError: 当 JSON 解析失败时
        ValueError: 当响应格式不正确时
    """
    # 清理响应文本（移除可能的 markdown 代码块标记）
    cleaned_text = response_text.strip()

    # 移除各种可能的 markdown 代码块标记
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```JSON"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    cleaned_text = cleaned_text.strip()

    # 尝试找到 JSON 数组的起始和结束位置
    start_idx = cleaned_text.find('[')
    if start_idx == -1:
        raise ValueError("响应中未找到 JSON 数组起始符号 '['")

    # 尝试找到匹配的结束括号
    bracket_count = 0
    end_idx = -1
    for i in range(start_idx, len(cleaned_text)):
        if cleaned_text[i] == '[':
            bracket_count += 1
        elif cleaned_text[i] == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end_idx = i + 1
                break

    if end_idx == -1:
        # 如果没有找到完整的结束括号，尝试修复截断的 JSON
        logger.warning("JSON 响应可能被截断，尝试修复...")
        last_complete_obj = cleaned_text.rfind('}')
        if last_complete_obj > start_idx:
            cleaned_text = cleaned_text[start_idx:last_complete_obj + 1] + ']'
        else:
            raise ValueError("无法修复截断的 JSON 响应")
    else:
        cleaned_text = cleaned_text[start_idx:end_idx]

    # 解析 JSON
    try:
        results = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败。响应内容: {cleaned_text[:500]}...")
        logger.error(f"完整响应: {response_text[:1000]}...")
        raise

    # 验证响应格式
    if not isinstance(results, list):
        raise ValueError(f"响应应为数组格式，实际: {type(results)}")

    # 创建原始评论的映射（用于合并）
    original_map = {r["review_id"]: r for r in original_batch}

    # 合并结果
    merged_results = []
    for result in results:
        review_id = result.get("review_id")

        if not review_id:
            logger.warning("响应中缺少 review_id，跳过")
            continue

        if review_id not in original_map:
            logger.warning(f"未找到对应的原始评论: {review_id}")
            continue

        # 合并原始数据和打标结果
        merged = {**original_map[review_id], **result}
        merged_results.append(merged)

    # 检查是否有评论未被处理
    if len(merged_results) < len(original_batch):
        missing_count = len(original_batch) - len(merged_results)
        logger.warning(f"有 {missing_count} 条评论未被正确处理，返回原始数据")

        # 添加未处理的评论（未打标）
        processed_ids = {r["review_id"] for r in merged_results}
        for original in original_batch:
            if original["review_id"] not in processed_ids:
                merged_results.append({
                    **original,
                    "sentiment": "解析失败",
                    "info_score": 0,
                    "tags": {}
                })

    return merged_results


def _get_failed_batch_results(
    batch: List[Dict],
    error_message: str
) -> List[Dict]:
    """为失败批次返回默认结果

    Args:
        batch: 原始评论批次
        error_message: 错误信息

    Returns:
        包含错误标记的评论列表
    """
    results = []
    for review in batch:
        results.append({
            **review,
            "sentiment": "分析失败",
            "info_score": 0,
            "tags": {},
            "_error": error_message
        })
    return results


def _retry_failed_batches(
    failed_batches: List[List[Dict]],
    failed_indices: List[int]
) -> List[Dict]:
    """重试失败的批次

    Args:
        failed_batches: 失败的批次列表
        failed_indices: 失败批次的原始索引

    Returns:
        重试成功的评论列表
    """
    results = []

    for batch, idx in zip(failed_batches, failed_indices):
        try:
            logger.info(f"重试批次 {idx + 1}")
            # 去掉冗余等待，加快重试响应 (V1.0 优化)
            batch_results = analyze_batch(batch)
            results.extend(batch_results)
            logger.info(f"批次 {idx + 1} 重试成功")
        except Exception as e:
            logger.error(f"批次 {idx + 1} 重试仍然失败: {str(e)}")
            # 重试失败，返回未打标的原始评论
            results.extend(_get_failed_batch_results(batch, f"RETRY_FAILED: {str(e)}"))

    return results


# ==================== 便捷函数 ====================

def analyze_single(review: Dict) -> Dict:
    """分析单条评论

    便捷函数，用于分析单条评论。内部会包装成批次调用。

    Args:
        review: 单条评论，需包含 review_id, body, rating

    Returns:
        添加了 sentiment, info_score, tags 的评论

    Example:
        >>> review = {"review_id": "1", "body": "...", "rating": 5}
        >>> result = analyze_single(review)
        >>> print(result["sentiment"])
        '强烈推荐'
    """
    results = analyze_batch([review])
    return results[0] if results else review


def get_analysis_stats(results: List[Dict]) -> Dict:
    """获取分析统计信息

    Args:
        results: analyze_all 返回的结果列表

    Returns:
        统计信息字典:
            - total: 总数
            - success: 成功数量
            - failed: 失败数量
            - sentiment_distribution: 情感分布
            - avg_info_score: 平均信息密度
    """
    total = len(results)

    if total == 0:
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "sentiment_distribution": {},
            "avg_info_score": 0
        }

    # 统计成功和失败
    failed = sum(1 for r in results if r.get("sentiment") in ["分析失败", "解析失败"])
    success = total - failed

    # 情感分布
    sentiment_dist = {}
    for r in results:
        s = r.get("sentiment", "未知")
        sentiment_dist[s] = sentiment_dist.get(s, 0) + 1

    # 平均信息密度（仅统计成功的）
    valid_scores = [r.get("info_score", 0) for r in results if r.get("info_score", 0) > 0]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "sentiment_distribution": sentiment_dist,
        "avg_info_score": round(avg_score, 2)
    }


if __name__ == "__main__":
    # 测试代码
    test_reviews = [
        {
            "review_id": "test_001",
            "body": "Amazing product! I bought this for my husband and he loves it. Great quality and fast shipping.",
            "rating": 5
        },
        {
            "review_id": "test_002",
            "body": "It's okay, does what it's supposed to do.",
            "rating": 3
        }
    ]

    print("测试 analyze_single:")
    result = analyze_single(test_reviews[0])
    print(f"Sentiment: {result.get('sentiment')}")
    print(f"Info Score: {result.get('info_score')}")
    print(f"Tags: {list(result.get('tags', {}).keys())}")

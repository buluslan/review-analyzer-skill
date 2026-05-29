"""
飞书同步模块 V2.1 - Lark CLI 集成（白板增强版）

核心流程：
1. 从 AI 报告中提取 mermaid 代码块
2. 将 mermaid 替换为 <whiteboard type="blank"> 占位符
3. lark-cli docs +create 创建文档（自动生成白板）
4. 用 mermaid 内容更新每个白板
5. 返回文档 URL + 白板渲染结果

所有操作均为非阻塞式 —— 失败时仅记录日志，不影响主流程。
"""

import json
import logging
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# lark-cli 命令名
_LARK_CLI_CMD = "lark-cli"


# ---------------------------------------------------------------------------
# 前置检测
# ---------------------------------------------------------------------------

def check_lark_cli() -> bool:
    """检测 lark-cli 是否已安装且可用。"""
    cli_path = shutil.which(_LARK_CLI_CMD)
    if not cli_path:
        logger.info("lark-cli 未安装或不在 PATH 中")
        return False

    try:
        result = subprocess.run(
            [_LARK_CLI_CMD, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = (result.stdout or result.stderr or "").strip()
            logger.info("lark-cli 可用: %s", version)
            return True
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Mermaid 提取与替换
# ---------------------------------------------------------------------------

def _extract_mermaid_blocks(markdown_content: str) -> List[Tuple[int, str]]:
    """从 Markdown 中提取所有 ```mermaid 代码块。

    Args:
        markdown_content: Markdown 文本

    Returns:
        [(位置索引, mermaid代码), ...] 列表
    """
    pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
    matches = pattern.finditer(markdown_content)
    blocks = []
    for idx, match in enumerate(matches):
        mermaid_code = match.group(1).strip()
        if mermaid_code:
            blocks.append((idx, mermaid_code))
    return blocks


def _replace_mermaid_with_whiteboard_tags(
    markdown_content: str,
) -> Tuple[str, List[str]]:
    """将 mermaid 代码块替换为飞书白板占位符。

    Args:
        markdown_content: 原始 Markdown（含 mermaid 代码块）

    Returns:
        (modified_markdown, mermaid_blocks) 元组：
        - modified_markdown: 替换后的 Markdown（含 <whiteboard type="blank"> 标签）
        - mermaid_blocks: 被提取的 mermaid 代码列表
    """
    mermaid_blocks = []
    modified = markdown_content

    # 用 finditer 定位所有 mermaid 块
    pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
    matches = list(pattern.finditer(modified))

    # 从后往前替换，避免偏移问题
    for match in reversed(matches):
        mermaid_code = match.group(1).strip()
        if mermaid_code:
            mermaid_blocks.insert(0, mermaid_code)  # 保持原始顺序
        # 替换为飞书白板占位符
        modified = modified[:match.start()] + "\n\n<whiteboard type=\"blank\"></whiteboard>\n\n" + modified[match.end():]

    return modified, mermaid_blocks


# ---------------------------------------------------------------------------
# 文档操作
# ---------------------------------------------------------------------------

def _create_doc_with_whiteboards(
    title: str,
    markdown_content: str,
) -> Dict[str, Any]:
    """创建飞书文档（含白板占位符）。

    Args:
        title: 文档标题
        markdown_content: 含 <whiteboard type="blank"> 的 Markdown

    Returns:
        {"success": bool, "doc_url": str, "doc_id": str, "board_tokens": list, "error": str}
    """
    result_payload: Dict[str, Any] = {
        "success": False,
        "doc_url": "",
        "doc_id": "",
        "board_tokens": [],
        "error": "",
    }

    try:
        cmd = [
            _LARK_CLI_CMD,
            "docs", "+create",
            "--title", title,
            "--markdown", markdown_content,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
        )

        if proc.returncode != 0:
            stderr = proc.stderr or proc.stdout or "未知错误"
            result_payload["error"] = f"lark-cli docs +create 失败: {stderr.strip()}"
            logger.error("创建飞书文档失败: %s", result_payload["error"])
            return result_payload

        # 解析 JSON 输出
        output = (proc.stdout or "").strip()
        try:
            data = json.loads(output)
            inner = data.get("data", data)
            result_payload["doc_url"] = inner.get("doc_url", _extract_url(output))
            result_payload["doc_id"] = inner.get("doc_id", "")
            result_payload["board_tokens"] = inner.get("board_tokens", [])
            result_payload["success"] = True
            logger.info(
                "飞书文档创建成功: %s (白板数: %d)",
                result_payload["doc_url"],
                len(result_payload["board_tokens"]),
            )
        except json.JSONDecodeError:
            # 降级：从输出中提取 URL
            doc_url = _extract_url(output)
            if doc_url:
                result_payload["doc_url"] = doc_url
                result_payload["success"] = True
                logger.info("飞书文档创建成功(URL模式): %s", doc_url)
            else:
                result_payload["error"] = f"无法解析文档输出: {output[:200]}"
                return result_payload

    except FileNotFoundError:
        result_payload["error"] = "lark-cli 未安装"
    except subprocess.TimeoutExpired:
        result_payload["error"] = "lark-cli 创建文档超时 (90s)"
    except Exception as exc:
        result_payload["error"] = f"创建文档异常: {exc}"

    return result_payload


def _update_whiteboard_with_mermaid(
    whiteboard_token: str,
    mermaid_code: str,
) -> Dict[str, Any]:
    """用 Mermaid 内容更新飞书白板。

    通过 stdin 管道传递 mermaid 内容，避免路径问题。

    Args:
        whiteboard_token: 白板 token
        mermaid_code: Mermaid 图表代码

    Returns:
        {"success": bool, "whiteboard_token": str, "error": str}
    """
    result_payload: Dict[str, Any] = {
        "success": False,
        "whiteboard_token": whiteboard_token,
        "error": "",
    }

    try:
        cmd = [
            _LARK_CLI_CMD,
            "whiteboard", "+update",
            "--whiteboard-token", whiteboard_token,
            "--source", "-",  # stdin
            "--input_format", "mermaid",
            "--overwrite",
        ]

        proc = subprocess.run(
            cmd,
            input=mermaid_code,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if proc.returncode != 0:
            stderr = proc.stderr or proc.stdout or "未知错误"
            result_payload["error"] = f"白板更新失败: {stderr.strip()}"
            logger.warning("白板 %s 更新失败: %s", whiteboard_token, result_payload["error"])
            return result_payload

        result_payload["success"] = True
        logger.info("白板 %s 更新成功", whiteboard_token)

    except FileNotFoundError:
        result_payload["error"] = "lark-cli 未安装"
    except subprocess.TimeoutExpired:
        result_payload["error"] = "白板更新超时 (60s)"
    except Exception as exc:
        result_payload["error"] = f"白板更新异常: {exc}"

    return result_payload


# ---------------------------------------------------------------------------
# URL 提取
# ---------------------------------------------------------------------------

def _extract_url(text: str) -> str:
    """从命令输出中提取第一个飞书 URL。"""
    url_pattern = r"https?://[^\s<>\"]+"
    match = re.search(url_pattern, text)
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# 核心接口
# ---------------------------------------------------------------------------

def sync_report(
    title: str,
    markdown_content: str,
    charts: Optional[list] = None,
) -> dict:
    """将报告和图表同步到飞书（V2.1 白板增强版）。

    流程：
      1. 提取 mermaid 代码块 → 替换为白板占位符
      2. lark-cli docs +create 创建文档 + 白板
      3. 逐个更新白板为 mermaid 图表
      4. 返回文档 URL + 白板状态

    Args:
        title: 报告标题
        markdown_content: Markdown 格式报告（可含 ```mermaid 代码块）
        charts: 保留兼容，当前未使用（图表通过 mermaid 代码块渲染）

    Returns:
        {
            "success": bool,
            "doc_url": str,
            "whiteboard_urls": list,  # 白板 token 列表
            "whiteboard_count": int,  # 成功渲染的白板数
            "error": str,
        }
    """
    result: Dict[str, Any] = {
        "success": False,
        "doc_url": "",
        "whiteboard_urls": [],
        "whiteboard_count": 0,
        "error": "",
    }

    # 1. 前置检查
    if not check_lark_cli():
        result["error"] = "lark-cli 不可用：未安装或未认证"
        logger.warning("飞书同步跳过: %s", result["error"])
        return result

    # 2. 提取 mermaid 并替换为白板占位符
    feishu_md, mermaid_blocks = _replace_mermaid_with_whiteboard_tags(markdown_content)
    logger.info("提取到 %d 个 mermaid 图表", len(mermaid_blocks))

    # 3. 创建飞书文档（含白板占位符）
    doc_result = _create_doc_with_whiteboards(title, feishu_md)
    if not doc_result["success"]:
        result["error"] = doc_result["error"]
        logger.warning("飞书文档创建失败: %s", doc_result["error"])
        return result

    result["doc_url"] = doc_result["doc_url"]
    result["success"] = True
    board_tokens = doc_result.get("board_tokens", [])

    # 4. 更新白板（如果有 mermaid 内容和白板 token）
    if mermaid_blocks and board_tokens:
        wb_count = min(len(mermaid_blocks), len(board_tokens))
        for i in range(wb_count):
            token = board_tokens[i]
            mermaid_code = mermaid_blocks[i]

            wb_result = _update_whiteboard_with_mermaid(token, mermaid_code)
            if wb_result["success"]:
                result["whiteboard_count"] += 1
                result["whiteboard_urls"].append(token)
            else:
                logger.warning(
                    "白板 %d/%d 渲染失败（不影响文档）: %s",
                    i + 1, wb_count, wb_result["error"],
                )

        # 有多余 mermaid 块没有对应白板
        if len(mermaid_blocks) > len(board_tokens):
            logger.warning(
                "有 %d 个 mermaid 图表超出白板数量，未渲染",
                len(mermaid_blocks) - len(board_tokens),
            )
    elif mermaid_blocks and not board_tokens:
        logger.warning("文档中未检测到白板 token，%d 个图表未渲染", len(mermaid_blocks))

    logger.info(
        "飞书同步完成: success=%s, doc=%s, 白板=%d/%d",
        result["success"],
        bool(result["doc_url"]),
        result["whiteboard_count"],
        len(mermaid_blocks),
    )
    return result


# ---------------------------------------------------------------------------
# 向后兼容：保留旧接口
# ---------------------------------------------------------------------------

def _create_doc(title: str, markdown_content: str) -> Dict[str, Any]:
    """旧接口兼容：创建飞书文档。"""
    result = _create_doc_with_whiteboards(title, markdown_content)
    return {
        "success": result["success"],
        "doc_url": result["doc_url"],
        "error": result["error"],
    }

"""
飞书同步模块 V2.0 - Lark CLI 集成

通过 lark-cli 和 lark-whiteboard 将报告和图表同步到飞书文档/白板。
所有操作均为非阻塞式 —— 失败时仅记录日志，不影响主流程。
"""

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# lark-cli 命令名
_LARK_CLI_CMD = "lark-cli"


# ---------------------------------------------------------------------------
# 前置检测
# ---------------------------------------------------------------------------

def check_lark_cli() -> bool:
    """检测 lark-cli 是否已安装且可用。

    Returns:
        True 表示可用，False 表示不可用。
    """
    cli_path = shutil.which(_LARK_CLI_CMD)
    if not cli_path:
        logger.info("lark-cli 未安装或不在 PATH 中")
        return False

    # 尝试执行 --version 或 --help 验证可用性
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
        else:
            logger.warning("lark-cli --version 返回非零: %s", result.stderr)
            return False
    except FileNotFoundError:
        logger.info("lark-cli 未找到")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("lark-cli --version 超时")
        return False
    except Exception as exc:
        logger.warning("lark-cli 检测异常: %s", exc)
        return False


# ---------------------------------------------------------------------------
# 文档创建
# ---------------------------------------------------------------------------

def _create_doc(title: str, markdown_content: str) -> Dict[str, Any]:
    """使用 lark-cli 创建飞书文档。

    Args:
        title: 文档标题
        markdown_content: Markdown 正文

    Returns:
        {"success": bool, "doc_url": str, "error": str}
    """
    result_payload: Dict[str, Any] = {
        "success": False,
        "doc_url": "",
        "error": "",
    }

    try:
        cmd = [
            _LARK_CLI_CMD,
            "docs",
            "+create",
            "--title", title,
            "--markdown", markdown_content,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if proc.returncode != 0:
            stderr = proc.stderr or proc.stdout or "未知错误"
            result_payload["error"] = f"lark-cli 返回非零 ({proc.returncode}): {stderr.strip()}"
            logger.error("创建飞书文档失败: %s", result_payload["error"])
            return result_payload

        # 解析输出中的 URL
        output = (proc.stdout or "").strip()
        doc_url = _extract_url(output)
        result_payload["success"] = True
        result_payload["doc_url"] = doc_url or output
        logger.info("飞书文档创建成功: %s", result_payload["doc_url"])

    except FileNotFoundError:
        result_payload["error"] = "lark-cli 未安装"
        logger.error("lark-cli 未安装，无法创建文档")
    except subprocess.TimeoutExpired:
        result_payload["error"] = "lark-cli 创建文档超时 (60s)"
        logger.error("创建飞书文档超时")
    except Exception as exc:
        result_payload["error"] = f"创建飞书文档异常: {exc}"
        logger.error("创建飞书文档异常: %s", exc)

    return result_payload


def _create_whiteboard_with_charts(
    title: str,
    chart_dsl_list: List[dict],
) -> Dict[str, Any]:
    """使用 lark-whiteboard 创建带图表的白板。

    将 chart engine 生成的 DSL 列表写入临时 JSON，
    然后调用 lark-cli whiteboard 子命令进行渲染。

    Args:
        title: 白板标题
        chart_dsl_list: lark-whiteboard DSL 格式的图表列表

    Returns:
        {"success": bool, "whiteboard_url": str, "error": str}
    """
    result_payload: Dict[str, Any] = {
        "success": False,
        "whiteboard_url": "",
        "error": "",
    }

    if not chart_dsl_list:
        result_payload["error"] = "无图表数据"
        return result_payload

    try:
        import tempfile

        # 将 DSL 列表写入临时文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump({"title": title, "charts": chart_dsl_list}, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name

        cmd = [
            _LARK_CLI_CMD,
            "whiteboard",
            "create",
            "--title", title,
            "--data", tmp_path,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # 清理临时文件
        try:
            import os
            os.unlink(tmp_path)
        except Exception:
            pass

        if proc.returncode != 0:
            stderr = proc.stderr or proc.stdout or "未知错误"
            result_payload["error"] = f"lark-cli whiteboard 返回非零 ({proc.returncode}): {stderr.strip()}"
            logger.error("创建飞书白板失败: %s", result_payload["error"])
            return result_payload

        output = (proc.stdout or "").strip()
        wb_url = _extract_url(output)
        result_payload["success"] = True
        result_payload["whiteboard_url"] = wb_url or output
        logger.info("飞书白板创建成功: %s", result_payload["whiteboard_url"])

    except FileNotFoundError:
        result_payload["error"] = "lark-cli 未安装"
        logger.error("lark-cli 未安装，无法创建白板")
    except subprocess.TimeoutExpired:
        result_payload["error"] = "lark-cli 创建白板超时 (60s)"
        logger.error("创建飞书白板超时")
    except Exception as exc:
        result_payload["error"] = f"创建飞书白板异常: {exc}"
        logger.error("创建飞书白板异常: %s", exc)

    return result_payload


# ---------------------------------------------------------------------------
# URL 提取
# ---------------------------------------------------------------------------

def _extract_url(text: str) -> str:
    """从命令输出中提取第一个 URL。"""
    import re

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
    """将报告和图表同步到飞书。

    该方法**永远不会抛出异常**，所有错误通过返回值报告。
    即使飞书同步完全失败，也不影响主流程。

    Args:
        title: 报告标题
        markdown_content: Markdown 格式的报告正文
        charts: 可选的图表配置列表（ChartConfig 对象或 lark-whiteboard DSL 字典）。
                如果提供，会尝试创建白板可视化。

    Returns:
        {
            "success": bool,
            "doc_url": str,
            "whiteboard_url": str,
            "error": str,
        }
        success 为 True 表示至少文档创建成功。
    """
    result: Dict[str, Any] = {
        "success": False,
        "doc_url": "",
        "whiteboard_url": "",
        "error": "",
    }

    # 1. 前置检查
    if not check_lark_cli():
        result["error"] = "lark-cli 不可用：未安装或未认证"
        logger.warning("飞书同步跳过: %s", result["error"])
        return result

    # 2. 创建飞书文档
    doc_result = _create_doc(title, markdown_content)
    if doc_result["success"]:
        result["doc_url"] = doc_result["doc_url"]
        result["success"] = True
    else:
        result["error"] = doc_result["error"]
        # 文档创建失败，不继续创建白板
        logger.warning("飞书文档创建失败，跳过白板创建: %s", doc_result["error"])
        return result

    # 3. 可选：创建白板图表
    if charts:
        try:
            # 将 ChartConfig 转换为飞书 DSL
            from src.chart_engine import ChartConfig, render_for_feishu

            dsl_list: List[dict] = []
            for chart in charts:
                if isinstance(chart, ChartConfig):
                    dsl_list.append(render_for_feishu(chart))
                elif isinstance(chart, dict):
                    dsl_list.append(chart)
                else:
                    logger.warning("跳过不支持的图表类型: %s", type(chart))

            if dsl_list:
                wb_result = _create_whiteboard_with_charts(
                    title=f"{title} - 图表看板",
                    chart_dsl_list=dsl_list,
                )
                if wb_result["success"]:
                    result["whiteboard_url"] = wb_result["whiteboard_url"]
                else:
                    # 白板创建失败不影响整体成功状态
                    logger.warning("飞书白板创建失败（不影响文档）: %s", wb_result["error"])
        except Exception as exc:
            logger.warning("飞书白板创建异常（不影响文档）: %s", exc)

    logger.info(
        "飞书同步完成: success=%s, doc=%s, wb=%s",
        result["success"],
        bool(result["doc_url"]),
        bool(result["whiteboard_url"]),
    )
    return result

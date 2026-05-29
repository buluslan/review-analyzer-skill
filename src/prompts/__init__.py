"""
Prompts 模块初始化

V2.0: 支持从 .md 文件加载 prompt 模板，保留对旧版 templates.py 的兼容。
"""

# 保留旧版导出（向后兼容）
from .templates import (
    TAGGING_PROMPT_SINGLE,
    TAGGING_PROMPT_BATCH,
    TAG_SYSTEM_TEXT,
    INSIGHTS_PROMPT_MD,
    get_tagging_prompt_batch,
    get_insights_prompt_md,
)

# V2.0 新增导出
from .manager import (
    PromptLoadError,
    build_insights_prompt,
    build_persona_prompt,
    build_tagging_prompt,
    get_active_chapters,
    get_chapter_info,
    list_chapters,
    load_chapter,
    load_prompt,
)

__all__ = [
    # 旧版兼容
    "TAGGING_PROMPT_SINGLE",
    "TAGGING_PROMPT_BATCH",
    "TAG_SYSTEM_TEXT",
    "INSIGHTS_PROMPT_MD",
    "get_tagging_prompt_batch",
    "get_insights_prompt_md",
    # V2.0 新增
    "PromptLoadError",
    "load_prompt",
    "load_chapter",
    "list_chapters",
    "get_active_chapters",
    "get_chapter_info",
    "build_tagging_prompt",
    "build_persona_prompt",
    "build_insights_prompt",
]

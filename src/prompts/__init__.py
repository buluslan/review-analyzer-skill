"""
Prompts 模块初始化

V2.1: 统一从 .md 文件加载 prompt 模板（单一真理源），
旧版 templates.py 已移除，打标/洞察 prompt 全部走 manager。
"""

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

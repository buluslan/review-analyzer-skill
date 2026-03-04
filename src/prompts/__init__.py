"""
Prompts 模块初始化
"""

from .templates import (
    TAGGING_PROMPT_SINGLE,
    TAGGING_PROMPT_BATCH,
    TAG_SYSTEM_TEXT,
    INSIGHTS_PROMPT_MD,
    get_tagging_prompt_batch,
    get_insights_prompt_md
)

__all__ = [
    "TAGGING_PROMPT_SINGLE",
    "TAGGING_PROMPT_BATCH",
    "TAG_SYSTEM_TEXT",
    "INSIGHTS_PROMPT_MD",
    "get_tagging_prompt_batch",
    "get_insights_prompt_md"
]

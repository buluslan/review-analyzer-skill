"""
数据采集模块 - 多源评论数据统一接入层

支持多种数据源:
- CSV/Excel 本地文件 (CsvFetcher)
- Sorftime 平台 (SorftimeFetcher) - 支持 MCP / API / CLI 三种连接模式

所有数据采集器继承自 DataFetcher 基类，提供统一的 fetch / list_fields / validate_config 接口。
"""

from typing import Dict, List

from src.data_fetchers.base import DataFetcher
from src.data_fetchers.csv_fetcher import CsvFetcher
from src.data_fetchers.sorftime_fetcher import SorftimeFetcher

# 可用数据采集器注册表: 名称 -> 实现类
FETCHER_REGISTRY: Dict[str, type] = {
    "csv": CsvFetcher,
    "sorftime": SorftimeFetcher,
}


def get_fetcher(name: str, **kwargs) -> DataFetcher:
    """根据名称获取数据采集器实例

    Args:
        name: 采集器名称，支持 "csv" 和 "sorftime"
        **kwargs: 传递给采集器构造函数的额外参数

    Returns:
        DataFetcher 实例

    Raises:
        ValueError: 当 name 不在注册表中时
    """
    name = name.lower().strip()
    if name not in FETCHER_REGISTRY:
        available = ", ".join(FETCHER_REGISTRY.keys())
        raise ValueError(
            f"未知的采集器: '{name}'，可选项: [{available}]"
        )
    return FETCHER_REGISTRY[name](**kwargs)


def list_fetchers() -> List[dict]:
    """列出所有已注册的采集器及其描述

    Returns:
        包含 name, description, fields 的字典列表
    """
    result = []
    for name, cls in FETCHER_REGISTRY.items():
        instance = cls()
        result.append({
            "name": name,
            "display_name": instance.get_name(),
            "fields": instance.list_fields(),
        })
    return result


__all__ = [
    "DataFetcher",
    "CsvFetcher",
    "SorftimeFetcher",
    "FETCHER_REGISTRY",
    "get_fetcher",
    "list_fetchers",
]

"""
数据采集器抽象基类

所有数据采集器（CSV、Sorftime 等）必须继承此基类并实现其抽象方法。
提供统一的数据获取接口，使上层业务代码无需关心具体数据来源。
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DataFetcher(ABC):
    """数据采集器抽象基类

    子类必须实现:
    - fetch(): 根据 ASIN 获取评论数据并输出为标准化 CSV
    - list_fields(): 声明该采集器支持的标准字段
    - validate_config(): 验证连接/配置是否可用
    - get_name(): 返回采集器的显示名称

    设计约定:
    - fetch() 返回一个 CSV 文件路径，文件使用 utf-8-sig 编码
    - CSV 文件的列名必须与 list_fields() 中的 name 一一对应
    - 所有子类构造函数接受可选的 config 字典，用于传递连接参数
    """

    def __init__(self, config: Optional[Dict] = None):
        """初始化采集器

        Args:
            config: 可选的配置字典，可能包含 API Key、文件路径等信息
        """
        self._config = config or {}

    @abstractmethod
    def fetch(self, asin: str, fields: List[str], site: str = "US") -> str:
        """获取评论数据并保存为标准化 CSV 文件

        Args:
            asin: Amazon Standard Identification Number（或通用商品标识）
            fields: 需要获取的标准字段列表（来自 list_fields 返回的 name）
            site: 站点代码，默认 "US"，可选 "UK"/"DE"/"JP" 等

        Returns:
            生成的 CSV 文件的绝对路径

        Raises:
            FileNotFoundError: 当数据源不可达时
            ValueError: 当 ASIN 无效或参数不合法时
            RuntimeError: 当数据获取过程中出现不可恢复错误时
        """
        ...

    @abstractmethod
    def list_fields(self) -> List[dict]:
        """列出此采集器支持的标准字段

        Returns:
            字段描述列表，每个元素为包含以下键的字典:
            - name (str): 标准字段名，如 "review_body", "rating"
            - description (str): 字段的中文描述
            - required (bool): 此字段是否为采集器必须输出的字段
        """
        ...

    @abstractmethod
    def validate_config(self) -> bool:
        """验证采集器配置/连接是否可用

        用于在执行 fetch 前预先检查:
        - 文件路径是否存在 (CsvFetcher)
        - API Key 是否有效 (SorftimeFetcher)
        - 网络连通性等

        Returns:
            True 表示配置有效，可以执行 fetch；False 表示不可用
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """返回采集器的显示名称

        Returns:
            如 "CSV本地文件", "Sorftime" 等
        """
        ...

    def get_config(self) -> Dict:
        """获取当前配置（只读副本）

        Returns:
            配置字典的浅拷贝
        """
        return dict(self._config)

    def update_config(self, updates: Dict) -> None:
        """更新配置参数

        Args:
            updates: 要合并到现有配置中的键值对
        """
        self._config.update(updates)
        logger.debug("配置已更新: %s", list(updates.keys()))

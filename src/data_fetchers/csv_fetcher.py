"""
CSV/Excel 本地文件数据采集器

封装现有 data_loader.py 的智能加载能力:
- 多编码自动检测 (utf-8 / utf-8-sig / gbk)
- 模糊列名嗅探 (中英文关键词匹配)
- URL 自动下载
- 数据清洗 (NaN 过滤、短文本过滤)
- 标准字段映射输出
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from src.data_fetchers.base import DataFetcher
from src.data_loader import download_if_url, load_reviews_from_file

logger = logging.getLogger(__name__)

# CSV 采集器支持的标准字段定义
CSV_STANDARD_FIELDS: List[dict] = [
    {
        "name": "review_id",
        "description": "评论唯一标识符（系统自动生成）",
        "required": True,
    },
    {
        "name": "review_title",
        "description": "评论标题",
        "required": False,
    },
    {
        "name": "review_body",
        "description": "评论正文内容",
        "required": True,
    },
    {
        "name": "rating",
        "description": "评分/星级 (1-5)",
        "required": False,
    },
    {
        "name": "review_date",
        "description": "评论日期",
        "required": False,
    },
    {
        "name": "reviewer_name",
        "description": "评论者名称",
        "required": False,
    },
    {
        "name": "verified_purchase",
        "description": "是否为已验证购买",
        "required": False,
    },
    {
        "name": "helpful_count",
        "description": "有帮助的投票数",
        "required": False,
    },
    {
        "name": "variant",
        "description": "商品变体/规格信息",
        "required": False,
    },
]


class CsvFetcher(DataFetcher):
    """CSV/Excel 本地文件数据采集器

    支持加载本地或远程(通过 URL)的 CSV / Excel 文件，
    利用 data_loader.py 的智能加载能力自动完成编码检测和列名映射，
    然后输出为标准化 CSV 文件。

    配置参数 (通过 config 字典传入):
        file_path (str): 数据文件路径或 URL。如果不提供，则需要在 fetch() 时
                         通过 asin 参数或配置中的 path 字段确定文件位置。
        output_dir (str): 输出目录，默认为系统临时目录。
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._file_path: Optional[str] = self._config.get("file_path")
        self._output_dir: str = self._config.get(
            "output_dir", os.path.join(os.getcwd(), "output")
        )

    def get_name(self) -> str:
        return "CSV本地文件"

    def list_fields(self) -> List[dict]:
        """返回 CSV 采集器支持的标准字段列表"""
        return list(CSV_STANDARD_FIELDS)

    def validate_config(self) -> bool:
        """验证文件路径是否可访问

        对于 URL 类路径始终返回 True（运行时才会下载）。
        对于本地文件，检查文件是否存在且可读。

        Returns:
            True 如果文件存在或路径为 URL
        """
        if self._file_path is None:
            logger.warning("未配置文件路径")
            return False

        path = self._file_path.strip()
        if path.startswith("http://") or path.startswith("https://"):
            # URL 路径在运行时才下载，此处不做预校验
            logger.debug("文件路径为 URL，跳过本地校验: %s", path)
            return True

        exists = os.path.isfile(path)
        if not exists:
            logger.warning("文件不存在: %s", path)
        return exists

    def fetch(self, asin: str, fields: List[str], site: str = "US") -> str:
        """加载 CSV/Excel 文件并输出标准化 CSV

        流程:
        1. 确定 source 文件路径 (config.file_path 或通过 asin 查找)
        2. 如果是 URL 则先下载
        3. 调用 data_loader.py 的 load_reviews_from_file 进行智能加载
        4. 将标准化数据映射到用户请求的 fields 并保存为 CSV

        Args:
            asin: 商品标识符，也用于从文件名推断数据源
            fields: 需要输出的标准字段列表
            site: 站点代码（CSV 模式下未使用，保留接口一致性）

        Returns:
            生成的标准化 CSV 文件绝对路径

        Raises:
            FileNotFoundError: 当文件不存在时
            ValueError: 当文件格式不支持或字段映射失败时
        """
        # Step 1: 确定源文件路径
        source_path = self._resolve_source_path(asin)
        logger.info("CSV 采集器: 正在加载文件 %s", source_path)

        # Step 2: URL 自动下载（委托给 data_loader）
        try:
            source_path = download_if_url(source_path)
        except ValueError as e:
            logger.error("文件下载失败: %s", e)
            raise

        if not os.path.exists(source_path):
            raise FileNotFoundError(f"数据文件不存在: {source_path}")

        # Step 3: 使用 data_loader 智能加载
        try:
            reviews, original_df = load_reviews_from_file(source_path)
        except Exception as e:
            logger.error("文件加载失败: %s", e)
            raise ValueError(f"加载文件失败: {e}") from e

        if not reviews:
            raise ValueError(f"文件加载成功但未提取到有效评论: {source_path}")

        logger.info("成功加载 %d 条评论记录", len(reviews))

        # Step 4: 映射到标准字段并保存
        output_path = self._save_standard_csv(reviews, asin, fields)
        logger.info("标准化 CSV 已保存: %s", output_path)
        return output_path

    def _resolve_source_path(self, asin: str) -> str:
        """解析源文件路径

        优先级:
        1. config.file_path (构造函数传入)
        2. data/{asin}.csv

        Args:
            asin: 商品标识符

        Returns:
            文件路径字符串
        """
        if self._file_path:
            return self._file_path

        # 尝试在 data 目录下按 ASIN 查找
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # 按优先级查找多种扩展名
        for ext in [".csv", ".xlsx", ".xls"]:
            candidate = data_dir / f"{asin}{ext}"
            if candidate.exists():
                return str(candidate)

        # 找不到精确匹配时，返回默认路径让上层报错
        default_path = data_dir / f"{asin}.csv"
        return str(default_path)

    def _save_standard_csv(
        self, reviews: List[dict], asin: str, fields: List[str]
    ) -> str:
        """将评论数据映射为标准字段并保存为 CSV

        将 data_loader 返回的 review_item（body/rating/date 等字段）
        映射为标准字段名（review_body/rating/review_date 等）。

        Args:
            reviews: load_reviews_from_file 返回的评论列表
            asin: 商品标识符，用于生成输出文件名
            fields: 需要输出的标准字段列表

        Returns:
            输出 CSV 文件路径
        """
        # 构建字段映射: data_loader 字段名 -> 标准字段名
        field_mapping = {
            "review_id": "review_id",
            "body": "review_body",
            "rating": "rating",
            "date": "review_date",
        }

        # 从原始数据中提取额外字段的模糊映射
        extra_mapping = {
            "review_title": ["标题", "title", "review_title"],
            "reviewer_name": ["评论者", "用户名", "reviewer_name", "name", "author"],
            "verified_purchase": ["verified", "verified_purchase", "是否验证"],
            "helpful_count": ["helpful", "helpful_count", "有帮助数"],
            "variant": ["variant", "变体", "规格", "style", "size"],
        }

        rows = []
        for review in reviews:
            row = {}
            original_data = review.get("_original_data", {})

            # 映射 data_loader 已处理的字段
            for src_key, std_key in field_mapping.items():
                if std_key in fields and src_key in review:
                    row[std_key] = review[src_key]

            # 从原始数据中模糊匹配额外字段
            original_cols = {
                str(k).lower(): k for k in original_data.keys()
            }
            for std_key, keywords in extra_mapping.items():
                if std_key not in fields:
                    continue
                matched_value = None
                for kw in keywords:
                    kw_lower = kw.lower()
                    for col_lower, col_orig in original_cols.items():
                        if kw_lower in col_lower:
                            val = original_data.get(col_orig)
                            if val is not None and str(val).strip() and str(val).lower() != "nan":
                                matched_value = val
                                break
                    if matched_value is not None:
                        break
                row[std_key] = matched_value if matched_value is not None else ""

            rows.append(row)

        # 确保只输出用户请求的字段（保持顺序）
        output_fields = [f for f in fields if any(f in row for row in rows)]
        if not output_fields:
            output_fields = fields  # fallback: 输出全部请求字段

        df = pd.DataFrame(rows, columns=output_fields)

        # 确保输出目录存在
        os.makedirs(self._output_dir, exist_ok=True)
        output_path = os.path.join(
            self._output_dir, f"评论采集及打标数据_{asin}.csv"
        )
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return os.path.abspath(output_path)

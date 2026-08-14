"""
卖家精灵（SellerSprite）评论数据采集器

通过卖家精灵 MCP 服务获取 Amazon 商品评论。
- 接口：MCP tools/call `review` @ https://mcp.sellersprite.com/mcp
- 认证：URL 参数 secret-key（用卖家精灵 MCP 密钥）
- 分页：每页最多 10 条，自动翻页至拿够 max_reviews 或无更多数据

注意：卖家精灵的 MCP 密钥与 REST API 密钥不通用。本采集器使用 MCP 密钥
（环境变量 SELLERSPRITE_SECRET_KEY），通过 MCP 服务（mcp.sellersprite.com）获取数据。

定位（重要）:
本采集器是「可选增强源」。CSV 是本工具主源（覆盖全、正文完整）。
卖家精灵适合「输入 ASIN 快速预览」场景，但有两个已知局限：
1. 单 ASIN 覆盖量有限（爆款可能也只有几十~百来条，远少于 Amazon 实际）
2. 部分评论的正文(content)字段缺失（仅有标题）——此时回退用标题作为正文
深度分析建议用 CSV（从任何平台导出完整评论）。
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

from src.data_fetchers.base import DataFetcher

logger = logging.getLogger(__name__)

# 卖家精灵 MCP 服务端点（MCP 密钥认证，非 REST）
SELLERSPRITE_MCP_URL = "https://mcp.sellersprite.com/mcp"
PAGE_SIZE_MAX = 10  # review 工具单页上限（size 最大 10）

# 卖家精灵采集器支持的标准字段定义
SELLERSPRITE_STANDARD_FIELDS: List[dict] = [
    {"name": "review_id", "description": "评论唯一标识符（系统自动生成）", "required": True},
    {"name": "asin", "description": "商品 ASIN 编码", "required": True},
    {"name": "review_title", "description": "评论标题", "required": True},
    {
        "name": "review_body",
        "description": "评论正文（content 缺失时回退用 title）",
        "required": True,
    },
    {"name": "rating", "description": "评分/星级 (1-5)", "required": True},
    {"name": "review_date", "description": "评论日期", "required": False},
    {"name": "reviewer_name", "description": "评论者名称", "required": False},
    {"name": "verified_purchase", "description": "是否已验证购买", "required": False},
    {"name": "helpful_count", "description": "有帮助的投票数", "required": False},
    {"name": "variant", "description": "商品变体/规格信息", "required": False},
]


class SellerspriteFetcher(DataFetcher):
    """卖家精灵评论数据采集器

    通过 MCP 服务 (https://mcp.sellersprite.com/mcp) 的 review 工具获取评论，
    输出与 CsvFetcher 同构的标准化 CSV，供下游打标/报告流程直接消费。

    配置参数 (通过 config 字典传入):
        secret_key (str): 卖家精灵 MCP secret-key（也可用环境变量 SELLERSPRITE_SECRET_KEY）
        max_reviews (int): 最多拉取条数（自动翻页），默认 100
        output_dir (str): 输出目录，默认为项目 output 目录
        api_timeout (int): 请求超时秒数，默认 60

    环境变量:
        SELLERSPRITE_SECRET_KEY: 认证密钥（优先级低于 config）
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._secret_key: str = self._config.get("secret_key", "") or os.environ.get(
            "SELLERSPRITE_SECRET_KEY", ""
        )
        self._max_reviews: int = int(self._config.get("max_reviews", 100))
        self._output_dir: str = self._config.get(
            "output_dir", str(Path(__file__).parent.parent.parent / "output")
        )
        self._api_timeout: int = int(self._config.get("api_timeout", 60))

    def get_name(self) -> str:
        return "卖家精灵 SellerSprite"

    def list_fields(self) -> List[dict]:
        """返回卖家精灵采集器支持的标准字段列表"""
        return list(SELLERSPRITE_STANDARD_FIELDS)

    def validate_config(self) -> bool:
        """验证卖家精灵配置是否可用（有 secret-key 即可）"""
        if not self._secret_key:
            logger.warning("卖家精灵: 未配置 secret-key")
            return False
        return True

    def fetch(self, asin: str, fields: List[str], site: str = "US") -> str:
        """通过卖家精灵 MCP 获取评论并保存为标准化 CSV

        Args:
            asin: Amazon ASIN 编码（10 位字母数字）
            fields: 需要输出的标准字段列表（可传 None 输出全部）
            site: Amazon 站点代码，默认 "US"

        Returns:
            标准化 CSV 文件的绝对路径

        Raises:
            ValueError: ASIN 格式无效或缺少认证信息
            RuntimeError: 数据获取失败
        """
        self._validate_asin(asin)
        if not self._secret_key:
            raise ValueError(
                "卖家精灵: 缺少 secret-key 认证密钥。"
                "请通过 config 或环境变量 SELLERSPRITE_SECRET_KEY 提供"
            )

        marketplace = site.upper()
        logger.info("卖家精灵: 正在获取 ASIN=%s, marketplace=%s", asin, marketplace)

        raw_reviews = self._fetch_all(asin, marketplace)
        if not raw_reviews:
            raise RuntimeError(
                f"卖家精灵: 未获取到评论数据 (ASIN={asin}, marketplace={marketplace})"
            )

        logger.info("卖家精灵: 获取到 %d 条评论", len(raw_reviews))
        return self._process_and_save(raw_reviews, asin, fields)

    # ==================== ASIN 校验 ====================

    @staticmethod
    def _validate_asin(asin: str) -> None:
        """校验 ASIN 格式（10 位字母数字）"""
        asin = asin.strip().upper()
        if not re.match(r"^[A-Z0-9]{10}$", asin):
            raise ValueError(f"ASIN 格式无效: '{asin}'，应为 10 位字母数字组合")

    # ==================== MCP 分页拉取 ====================

    def _fetch_all(self, asin: str, marketplace: str) -> List[dict]:
        """通过 MCP endpoint 分页拉取评论（JSON-RPC tools/call）

        MCP 响应结构：
            {"jsonrpc":"2.0","result":{"content":[{"type":"text","text":"<内层JSON>"}]}}
        内层 JSON（text 字段，需二次解析）：
            {"code":"OK","data":{"items":[...],"total":N,"pages":M}}

        Args:
            asin: 商品 ASIN
            marketplace: 站点代码

        Returns:
            原始评论列表（已截断至 max_reviews）
        """
        reviews: List[dict] = []
        page = 1
        url = f"https://mcp.sellersprite.com/mcp?secret-key={self._secret_key}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        while len(reviews) < self._max_reviews:
            size = min(PAGE_SIZE_MAX, self._max_reviews - len(reviews))
            payload = {
                "jsonrpc": "2.0",
                "id": page,
                "method": "tools/call",
                "params": {
                    "name": "review",
                    "arguments": {
                        "marketplace": marketplace,
                        "asin": asin.upper(),
                        "page": page,
                        "size": size,
                    },
                },
            }

            try:
                resp = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._api_timeout,
                )
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                code = e.response.status_code if e.response is not None else "N/A"
                if code == 401:
                    raise RuntimeError("卖家精灵认证失败: secret-key 无效或已过期")
                if code == 429:
                    raise RuntimeError("卖家精灵请求频率超限，请稍后重试")
                raise RuntimeError(f"卖家精灵 HTTP 错误 {code}: {e}")
            except requests.exceptions.Timeout:
                raise RuntimeError(f"卖家精灵请求超时 ({self._api_timeout}s)")
            except requests.exceptions.ConnectionError as e:
                raise RuntimeError(f"卖家精灵连接失败: {e}")

            # MCP 响应：result.content[0].text 是一个 JSON 字符串，需二次解析
            rpc = resp.json()
            if rpc.get("error"):
                raise RuntimeError(f"卖家精灵 MCP 错误: {rpc['error']}")
            content = (rpc.get("result") or {}).get("content") or []
            text = content[0].get("text", "{}") if content else "{}"
            try:
                inner = json.loads(text)
            except (ValueError, TypeError) as e:
                raise RuntimeError(f"卖家精灵响应解析失败: {e}")

            # 内层 code 检查（认证/权限错误在此暴露，如 ERROR_UNAUTHORIZED）
            if inner.get("code") != "OK":
                raise RuntimeError(
                    f"卖家精灵返回 {inner.get('code')}: {inner.get('message')}"
                )

            data_node = inner.get("data") or {}
            items = data_node.get("items") or []
            if not items:
                break

            reviews.extend(items)
            total = data_node.get("total", 0)
            # 拿够、或本页未满（说明已到尾页）、或超过接口总量
            if len(reviews) >= total or len(items) < size:
                break
            page += 1

        return reviews[: self._max_reviews]

    # ==================== 字段映射 + 保存 ====================

    def _process_and_save(
        self, raw_reviews: List[dict], asin: str, fields: Optional[List[str]]
    ) -> str:
        """将卖家精灵原始评论映射为标准字段并保存为 CSV

        字段映射:
            author  -> reviewer_name
            title   -> review_title
            content -> review_body （缺失时回退 title）
            date    -> review_date （毫秒时间戳 -> YYYY-MM-DD）
            star    -> rating
            verified-> verified_purchase
            likes   -> helpful_count
            skus    -> variant
        """
        rows = []
        for idx, item in enumerate(raw_reviews, 1):
            content = (item.get("content") or "").strip()
            title = (item.get("title") or "").strip()
            # content 经常缺失，回退用 title 保证有正文可打标
            body = content if content else title

            rows.append(
                {
                    "review_id": f"{asin}-{idx}",
                    "asin": asin,
                    "review_title": title,
                    "review_body": body,
                    "rating": item.get("star"),
                    "review_date": self._ts_to_date(item.get("date")),
                    "reviewer_name": item.get("author") or "",
                    "verified_purchase": item.get("verified"),
                    "helpful_count": item.get("likes"),
                    "variant": self._join_skus(item.get("skus")),
                }
            )

        # 确定输出列
        if fields:
            all_keys = list(rows[0].keys()) if rows else []
            output_fields = [f for f in fields if f in all_keys] or all_keys
        else:
            output_fields = list(rows[0].keys()) if rows else []

        df = pd.DataFrame(rows, columns=output_fields) if rows else pd.DataFrame()
        os.makedirs(self._output_dir, exist_ok=True)
        output_path = os.path.join(
            self._output_dir, f"评论采集及打标数据_{asin}.csv"
        )
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return os.path.abspath(output_path)

    @staticmethod
    def _ts_to_date(ts) -> str:
        """毫秒时间戳 -> YYYY-MM-DD"""
        if not ts:
            return ""
        try:
            return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
        except (TypeError, ValueError, OSError):
            return ""

    @staticmethod
    def _join_skus(skus) -> str:
        """sku 列表 -> 分号分隔字符串"""
        if not skus:
            return ""
        if isinstance(skus, list):
            return "; ".join(str(s) for s in skus if s)
        return str(skus)

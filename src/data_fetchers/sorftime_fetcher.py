"""
Sorftime 平台数据采集器

支持三种连接模式:
- MCP (默认，推荐在 Agent 环境中使用)
- API (HTTP POST，SSE 流式响应)
- CLI (命令行工具调用)

Sorftime API 特性:
- 每次 API 调用最多返回 100 条评论
- 评论时间范围: 最近 1 年
- 使用 Account-SK 进行认证
- 响应格式为 SSE (Server-Sent Events)，需流式解析
- 中文文本可能以 Unicode 转义序列形式返回，需要解码
"""

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import pandas as pd
import requests

from src.data_fetchers.base import DataFetcher

logger = logging.getLogger(__name__)

# Sorftime API 端点
SORFTIME_API_URL = "https://mcp.sorftime.com"

# 最大获取评论数 / 时间范围
MAX_REVIEWS_PER_CALL = 100
REVIEW_DATE_RANGE = "1y"  # 1 年

# Sorftime 支持的站点代码映射
SITE_CODE_MAP = {
    "US": "US",
    "UK": "UK",
    "DE": "DE",
    "FR": "FR",
    "JP": "JP",
    "IT": "IT",
    "ES": "ES",
    "CA": "CA",
    "AU": "AU",
    "MX": "MX",
    "IN": "IN",
    "BR": "BR",
}

# Sorftime 原始字段 -> 标准字段 映射
SORFTIME_FIELD_MAPPING = {
    "reviewTitle": "review_title",
    "reviewBody": "review_body",
    "rating": "rating",
    "date": "review_date",
    "reviewerName": "reviewer_name",
    "verifiedPurchase": "verified_purchase",
    "helpfulVotes": "helpful_count",
    "variant": "variant",
    "asin": "asin",
    "reviewId": "review_id",
}

# Sorftime 采集器支持的标准字段定义
SORFTIME_STANDARD_FIELDS: List[dict] = [
    {
        "name": "review_id",
        "description": "评论唯一标识符",
        "required": True,
    },
    {
        "name": "asin",
        "description": "商品 ASIN 编码",
        "required": True,
    },
    {
        "name": "review_title",
        "description": "评论标题",
        "required": True,
    },
    {
        "name": "review_body",
        "description": "评论正文内容",
        "required": True,
    },
    {
        "name": "rating",
        "description": "评分/星级 (1-5)",
        "required": True,
    },
    {
        "name": "review_date",
        "description": "评论日期",
        "required": True,
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


class SorftimeFetcher(DataFetcher):
    """Sorftime 平台数据采集器

    通过 MCP / API / CLI 三种模式获取 Amazon 商品评论数据。

    配置参数 (通过 config 字典传入):
        mode (str): 连接模式 "mcp" | "api" | "cli"，默认 "mcp"
        account_sk (str): Sorftime Account-SK 认证密钥
                          也可通过环境变量 SORFTIME_ACCOUNT_SK 提供
        output_dir (str): 输出目录，默认为项目 output 目录
        api_timeout (int): API 请求超时秒数，默认 120
        cli_path (str): Sorftime CLI 可执行文件路径，默认 "sorftime"

    环境变量:
        SORFTIME_ACCOUNT_SK: Account-SK 认证密钥（优先级低于 config）
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._mode: str = self._config.get("mode", "mcp").lower()
        self._account_sk: str = self._config.get(
            "account_sk", ""
        ) or os.environ.get("SORFTIME_ACCOUNT_SK", "")
        self._output_dir: str = self._config.get(
            "output_dir",
            str(Path(__file__).parent.parent.parent / "output"),
        )
        self._api_timeout: int = self._config.get("api_timeout", 120)
        self._cli_path: str = self._config.get("cli_path", "sorftime")

        if self._mode not in ("mcp", "api", "cli"):
            logger.warning(
                "不支持的连接模式: '%s'，回退到 MCP 模式", self._mode
            )
            self._mode = "mcp"

    def get_name(self) -> str:
        return "Sorftime"

    def list_fields(self) -> List[dict]:
        """返回 Sorftime 采集器支持的标准字段列表"""
        return list(SORFTIME_STANDARD_FIELDS)

    def validate_config(self) -> bool:
        """验证 Sorftime 配置是否可用

        根据连接模式分别检查:
        - MCP 模式: 检查是否有 Account-SK
        - API 模式: 检查 Account-SK 并尝试连接 API 端点
        - CLI 模式: 检查 CLI 工具是否可执行

        Returns:
            True 如果配置验证通过
        """
        # 共通检查: Account-SK 必须存在
        if not self._account_sk:
            logger.warning("Sorftime: 未配置 Account-SK")
            return False

        if self._mode == "api":
            return self._validate_api_mode()
        elif self._mode == "cli":
            return self._validate_cli_mode()
        else:
            # MCP 模式: 有 SK 即可，实际连接在 fetch 时建立
            logger.debug("Sorftime MCP 模式: Account-SK 已配置 (%s...)",
                         self._mask_sk())
            return True

    def fetch(self, asin: str, fields: List[str], site: str = "US") -> str:
        """通过 Sorftime 获取评论数据

        Args:
            asin: Amazon ASIN 编码（10 位字母数字）
            fields: 需要获取的标准字段列表
            site: Amazon 站点代码，默认 "US"

        Returns:
            标准化 CSV 文件的绝对路径

        Raises:
            ValueError: ASIN 格式无效或缺少认证信息
            RuntimeError: 数据获取失败
        """
        # 参数校验
        self._validate_asin(asin)
        if not self._account_sk:
            raise ValueError(
                "Sorftime: 缺少 Account-SK 认证密钥。"
                "请通过 config 或环境变量 SORFTIME_ACCOUNT_SK 提供"
            )

        site = site.upper()
        if site not in SITE_CODE_MAP:
            logger.warning("未知站点代码 '%s'，使用默认 US", site)
            site = "US"

        logger.info(
            "Sorftime [%s 模式]: 正在获取 ASIN=%s, site=%s",
            self._mode.upper(), asin, site,
        )

        # 根据模式分发
        if self._mode == "mcp":
            raw_data = self._fetch_via_mcp(asin, site)
        elif self._mode == "api":
            raw_data = self._fetch_via_api(asin, site)
        elif self._mode == "cli":
            raw_data = self._fetch_via_cli(asin, site)
        else:
            raise RuntimeError(f"未知的连接模式: {self._mode}")

        if not raw_data:
            raise RuntimeError(
                f"Sorftime: 未获取到评论数据 (ASIN={asin}, site={site})"
            )

        logger.info("Sorftime: 获取到 %d 条原始评论", len(raw_data))

        # 字段映射 + Unicode 解码 + 保存为标准化 CSV
        return self._process_and_save(raw_data, asin, fields)

    # ==================== ASIN 校验 ====================

    @staticmethod
    def _validate_asin(asin: str) -> None:
        """校验 ASIN 格式

        Amazon ASIN 通常是 10 位字母数字组合。

        Args:
            asin: 待校验的 ASIN 字符串

        Raises:
            ValueError: ASIN 格式不合法
        """
        asin = asin.strip().upper()
        if not re.match(r"^[A-Z0-9]{10}$", asin):
            raise ValueError(
                f"ASIN 格式无效: '{asin}'，应为 10 位字母数字组合"
            )

    # ==================== MCP 模式 ====================

    def _fetch_via_mcp(self, asin: str, site: str) -> List[dict]:
        """通过 MCP 协议获取评论数据

        MCP 模式是推荐用于 Agent 环境的连接方式。
        当前实现使用 HTTP POST 模拟 MCP 调用（兼容 MCP-over-HTTP），
        未来可替换为原生 MCP SDK。

        Args:
            asin: 商品 ASIN
            site: 站点代码

        Returns:
            原始评论数据列表

        Raises:
            RuntimeError: MCP 调用失败
        """
        logger.info("Sorftime MCP: 发起 MCP 调用")

        payload = {
            "tool": "get_reviews",
            "params": {
                "asin": asin.upper(),
                "amzSite": site,
                "maxCount": MAX_REVIEWS_PER_CALL,
                "dateRange": REVIEW_DATE_RANGE,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Account-SK": self._account_sk,
            "Accept": "text/event-stream",
        }

        try:
            response = requests.post(
                SORFTIME_API_URL,
                json=payload,
                headers=headers,
                timeout=self._api_timeout,
                stream=True,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Sorftime MCP 请求超时 ({self._api_timeout}s)"
            )
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Sorftime MCP 连接失败: {e}"
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "N/A"
            raise RuntimeError(
                f"Sorftime MCP HTTP 错误 {status_code}: {e}"
            )

        return self._parse_sse_response(response)

    # ==================== API 模式 ====================

    def _fetch_via_api(self, asin: str, site: str) -> List[dict]:
        """通过 Sorftime REST API 获取评论数据

        使用 POST 请求，响应为 SSE 流式格式。

        Args:
            asin: 商品 ASIN
            site: 站点代码

        Returns:
            原始评论数据列表
        """
        payload = {
            "asin": asin.upper(),
            "amzSite": site,
            "reviewType": "all",
            "maxCount": MAX_REVIEWS_PER_CALL,
            "dateRange": REVIEW_DATE_RANGE,
        }

        headers = {
            "Content-Type": "application/json",
            "Account-SK": self._account_sk,
            "Accept": "text/event-stream",
        }

        logger.debug("Sorftime API: POST %s", SORFTIME_API_URL)

        try:
            response = requests.post(
                SORFTIME_API_URL,
                json=payload,
                headers=headers,
                timeout=self._api_timeout,
                stream=True,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Sorftime API 请求超时 ({self._api_timeout}s)"
            )
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Sorftime API 连接失败: {e}")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "N/A"
            if status_code == 401:
                raise RuntimeError(
                    "Sorftime API 认证失败: Account-SK 无效或已过期"
                )
            elif status_code == 429:
                raise RuntimeError(
                    "Sorftime API 请求频率超限，请稍后重试"
                )
            raise RuntimeError(
                f"Sorftime API HTTP 错误 {status_code}: {e}"
            )

        return self._parse_sse_response(response)

    # ==================== CLI 模式 ====================

    def _fetch_via_cli(self, asin: str, site: str) -> List[dict]:
        """通过 Sorftime CLI 工具获取评论数据

        Args:
            asin: 商品 ASIN
            site: 站点代码

        Returns:
            原始评论数据列表

        Raises:
            FileNotFoundError: CLI 工具不存在
            RuntimeError: CLI 执行失败
        """
        cmd = [
            self._cli_path,
            "reviews",
            "--asin", asin.upper(),
            "--site", site,
            "--max", str(MAX_REVIEWS_PER_CALL),
            "--range", REVIEW_DATE_RANGE,
            "--sk", self._account_sk,
            "--format", "json",
        ]

        logger.debug("Sorftime CLI: %s", " ".join(cmd[:-2]))  # 不打 SK

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._api_timeout,
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Sorftime CLI 工具不存在: {self._cli_path}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Sorftime CLI 执行超时 ({self._api_timeout}s)"
            )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Sorftime CLI 执行失败 (exit={result.returncode}): {stderr}"
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Sorftime CLI 输出解析失败: {e}"
            )

        # CLI 可能返回列表或包含 reviews 键的字典
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("reviews", data.get("data", []))
        return []

    # ==================== SSE 响应解析 ====================

    def _parse_sse_response(self, response: requests.Response) -> List[dict]:
        """解析 Sorftime SSE 流式响应

        SSE 数据格式示例:
            data: {"reviews": [...]}
            data: {"reviews": [...]}
            data: [DONE]

        每行以 "data: " 开头，包含 JSON 片段。最终累积合并为评论列表。

        Args:
            response: requests.Response 对象（已启用 stream=True）

        Returns:
            累积的评论数据列表
        """
        all_reviews: List[dict] = []

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            # SSE 行格式: "data: {json}"
            if not line.startswith("data: "):
                continue

            payload = line[6:]  # 去掉 "data: " 前缀

            # 流结束标记
            if payload.strip() == "[DONE]":
                logger.debug("SSE 流结束标记 [DONE]")
                break

            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning("SSE 数据行 JSON 解析失败，跳过: %s", payload[:100])
                continue

            # 解析不同响应结构
            reviews_chunk = self._extract_reviews_from_chunk(chunk)
            all_reviews.extend(reviews_chunk)

        return all_reviews

    @staticmethod
    def _extract_reviews_from_chunk(chunk: Any) -> List[dict]:
        """从 SSE chunk 中提取评论列表

        Sorftime 可能返回多种数据结构:
        - {"reviews": [...]}
        - {"data": {"reviews": [...]}}
        - 直接是评论列表 [...]
        - {"review": {...}}  (单条评论)

        Args:
            chunk: 解析后的 JSON 对象

        Returns:
            评论字典列表
        """
        if isinstance(chunk, list):
            return chunk
        if isinstance(chunk, dict):
            # 优先查找 reviews 键
            if "reviews" in chunk:
                data = chunk["reviews"]
                return data if isinstance(data, list) else [data]
            if "data" in chunk:
                inner = chunk["data"]
                if isinstance(inner, list):
                    return inner
                if isinstance(inner, dict) and "reviews" in inner:
                    data = inner["reviews"]
                    return data if isinstance(data, list) else [data]
            # 单条评论
            if "reviewBody" in chunk or "review_body" in chunk:
                return [chunk]
        return []

    # ==================== 字段映射 & 数据处理 ====================

    def _process_and_save(
        self, raw_data: List[dict], asin: str, fields: List[str]
    ) -> str:
        """处理原始数据: Unicode 解码 + 字段映射 + 保存 CSV

        Args:
            raw_data: Sorftime 返回的原始评论列表
            asin: 商品 ASIN
            fields: 需要输出的标准字段列表

        Returns:
            标准化 CSV 文件绝对路径
        """
        mapped_rows = []
        for idx, raw_review in enumerate(raw_data):
            row = self._map_single_review(raw_review, asin, idx)
            mapped_rows.append(row)

        # 只保留用户请求的字段
        output_fields = [f for f in fields if f in SORFTIME_FIELD_MAPPING.values()]
        # 确保核心字段始终存在
        for core_field in ("review_id", "review_body"):
            if core_field not in output_fields:
                output_fields.insert(0, core_field)

        df = pd.DataFrame(mapped_rows, columns=output_fields)

        # 清洗: 过滤空评论
        initial_count = len(df)
        if "review_body" in df.columns:
            df = df.dropna(subset=["review_body"])
            df = df[df["review_body"].astype(str).str.strip().str.len() >= 3]
        dropped = initial_count - len(df)
        if dropped > 0:
            logger.info("数据清洗: 过滤 %d 条无效评论", dropped)

        # 保存 CSV
        os.makedirs(self._output_dir, exist_ok=True)
        output_path = os.path.join(
            self._output_dir, f"评论采集及打标数据_{asin}.csv"
        )
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return os.path.abspath(output_path)

    def _map_single_review(
        self, raw: dict, asin: str, index: int
    ) -> dict:
        """将单条 Sorftime 原始数据映射为标准字段

        包含 Unicode 转义解码逻辑（Sorftime 中文可能以 \\uXXXX 返回）。

        Args:
            raw: 原始评论字典
            asin: 商品 ASIN
            index: 序号（用于生成 review_id）

        Returns:
            标准字段字典
        """
        row: Dict[str, Any] = {}

        # 反向映射: 标准字段 -> Sorftime 原始键
        reverse_map = {v: k for k, v in SORFTIME_FIELD_MAPPING.items()}

        for std_field, sorf_key in reverse_map.items():
            value = raw.get(sorf_key, "")
            # 备用: 尝试下划线命名（某些接口版本可能用 snake_case）
            if value == "" and std_field != sorf_key:
                value = raw.get(std_field, "")

            # Unicode 转义解码
            if isinstance(value, str):
                value = self._decode_unicode_escapes(value)

            row[std_field] = value

        # 确保 review_id 和 asin 存在
        if not row.get("review_id"):
            row["review_id"] = f"{asin}-{index:04d}"
        if not row.get("asin"):
            row["asin"] = asin.upper()

        # 数值类型转换
        if "rating" in row:
            try:
                row["rating"] = float(row["rating"])
            except (ValueError, TypeError):
                row["rating"] = 0.0

        if "helpful_count" in row:
            try:
                row["helpful_count"] = int(row["helpful_count"])
            except (ValueError, TypeError):
                row["helpful_count"] = 0

        return row

    @staticmethod
    def _decode_unicode_escapes(text: str) -> str:
        """解码 Unicode 转义序列

        Sorftime 返回的中文文本可能以 \\uXXXX 形式编码，
        需要将其解码为正常中文字符。

        Args:
            text: 可能包含 Unicode 转义的字符串

        Returns:
            解码后的字符串

        Examples:
            >>> _decode_unicode_escapes("\\u4f60\\u597d")
            '你好'
        """
        if not text or "\\u" not in text:
            return text

        try:
            # codecs.decode 不处理混合内容，使用 encode/decode 组合
            return text.encode("utf-8").decode("unicode_escape")
        except (UnicodeDecodeError, UnicodeEncodeError):
            # 混合内容（中英文混合 + unicode 转义）回退方案:
            # 逐个匹配 \\uXXXX 并替换
            def replace_unicode(match: re.Match) -> str:
                code_point = match.group(1)
                try:
                    return chr(int(code_point, 16))
                except (ValueError, OverflowError):
                    return match.group(0)

            return re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode, text)

    # ==================== 配置验证辅助 ====================

    def _validate_api_mode(self) -> bool:
        """验证 API 模式配置"""
        if not self._account_sk:
            return False

        try:
            # 发送轻量级请求验证连接和认证
            headers = {
                "Content-Type": "application/json",
                "Account-SK": self._account_sk,
            }
            resp = requests.get(
                SORFTIME_API_URL,
                headers=headers,
                timeout=15,
            )
            # 2xx 或 404 都说明连接正常（404 可能是根路径无处理）
            if resp.status_code < 500:
                logger.info(
                    "Sorftime API 连接正常 (HTTP %d)", resp.status_code
                )
                return True
            logger.warning(
                "Sorftime API 连接异常 (HTTP %d)", resp.status_code
            )
            return False
        except requests.exceptions.RequestException as e:
            logger.warning("Sorftime API 连接失败: %s", e)
            return False

    def _validate_cli_mode(self) -> bool:
        """验证 CLI 模式配置"""
        import shutil

        cli_found = shutil.which(self._cli_path) is not None
        if not cli_found:
            logger.warning(
                "Sorftime CLI 工具不存在: %s", self._cli_path
            )
        return cli_found

    def _mask_sk(self) -> str:
        """掩码显示 Account-SK"""
        if not self._account_sk or len(self._account_sk) < 8:
            return "***"
        return f"{'*' * 8}{self._account_sk[-4:]}"

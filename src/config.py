"""
配置管理模块 V1.0

重大变更：双模洞察系统
- 支持双模式生成洞察报告：CLI 原生版 / Gemini API
- CLI 模式：使用 subprocess 调用宿主系统的 Claude Code CLI (claude -p)
- Gemini 模式：使用 Google Gemini API 生成高质量洞察报告
- 打标阶段固定使用 CLI（config.CLAUDE_CLI_CMD），不能用 API
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class Config:
    """全局配置类 V1.0 - CLI 原生版"""

    # ==================== 项目路径配置 ====================
    PROJECT_ROOT: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    # 输出目录: 支持环境变量 OUTPUT_DIR 或命令行参数 --output-dir
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./output")))
    REFERENCES_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "references")
    ASSETS_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "assets")
    DATA_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")

    # ==================== Claude Code CLI 配置 ====================
    # 使用宿主系统的 Claude Code CLI 进行 AI 推理
    # 通过 subprocess.run(["claude", "-p", ...]) 调用
    CLAUDE_CLI_CMD: str = "claude"
    # CLI 调用超时时间（秒）- 从环境变量读取，默认 180 秒
    CLI_TIMEOUT: int = int(os.getenv("CLI_TIMEOUT", "600"))

    # ==================== 分析配置 ====================
    MAX_REVIEWS: int = 500           # 最大获取评论数
    BATCH_SIZE: int = 30             # 每批处理数量 (30-50条)
    TAG_SYSTEM_PATH: str = "tag_system.yaml"

    # ==================== 用户画像配置 ====================
    PERSONA_MIN_COUNT: int = 3       # 成为画像的最小样本数
    MAX_PERSONAS: int = 4            # 最多识别的用户画像数
    SAMPLES_PER_PERSONA: int = 6     # 每个画像的样本数 (3正+3负)

    # ==================== 输出配置 ====================
    GENERATE_HTML: bool = True       # 是否生成 HTML 报告
    CSV_ENCODING: str = "utf-8-sig"  # CSV 文件编码
    PROJECT_NAME: str = "评论分析项目"  # 项目名称

    # ==================== 并发配置 ====================
    # 最大并发子进程数（调用 claude -p）- 从环境变量读取，默认 2
    MAX_CONCURRENT_AGENTS: int = int(os.getenv("MAX_CONCURRENT", "2"))

    # ==================== 快速模式配置 ====================
    QUICK_MODE_MAX_REVIEWS: int = 30  # 快速模式默认获取评论数

    # ==================== 洞察报告生成配置 ====================
    INSIGHTS_PROVIDER: str = "cli"  # 可选: cli / gemini
    INSIGHTS_FORMAT: str = "txt"  # 可选: md / txt
    GEMINI_API_KEY: str = ""  # 从环境变量读取或用户输入
    GEMINI_MODEL: str = "gemini-3-flash-preview"  # 使用 Gemini 3 Flash Preview
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 8192

    # ==================== HTML 报告生成配置 V1.0 =============
    HTML_GENERATION_MODEL: str = os.getenv("HTML_REPORT_MODEL", "gemini-3.1-pro-preview")
    HTML_GENERATION_TEMPERATURE: float = 0.8  # 创意温度更高
    HTML_CREATOR_NAME: str = os.getenv("HTML_CREATOR_NAME", "Buluu@新西楼")
    HTML_SYSTEM_PROMPT_PATH: str = "prompt_html.md"  # 黑金奢华提示词路径
    HTML_GENERATION_SOURCE: str = "gemini"          # 可选: gemini / local

    def __post_init__(self):
        """初始化后验证"""
        # 确保输出目录存在
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 验证 Claude CLI 是否可用
        import shutil
        if not shutil.which(self.CLAUDE_CLI_CMD):
            raise RuntimeError(
                f"❌ 找不到 Claude Code CLI！请确保已安装 Claude Code 并将 '{self.CLAUDE_CLI_CMD}' 加入 PATH"
            )

    def _get_project_dir(self, asin: str) -> Path:
        """获取项目输出目录: {ASIN}-{PROJECT_NAME}-{月.日}"""
        date_str = datetime.now().strftime("%-m.%-d")  # 格式: 2.13 (macOS)
        # 兼容不同系统的日期格式
        try:
            date_str = datetime.now().strftime("%-m.%-d")
        except ValueError:
            try:
                date_str = datetime.now().strftime("%#m.%#d")
            except ValueError:
                date_str = datetime.now().strftime("%m.%d").lstrip("0").replace(".0", ".")

        project_dir = self.OUTPUT_DIR / f"{asin}-{self.PROJECT_NAME}-{date_str}"
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    @property
    def tag_system_path(self) -> Path:
        """获取标签体系配置文件路径"""
        return self.REFERENCES_DIR / self.TAG_SYSTEM_PATH

    @property
    def template_path(self) -> Path:
        """获取 HTML 模板文件路径"""
        return self.ASSETS_DIR / "report.html"

    def get_csv_path(self, asin: str) -> Path:
        """获取 CSV 输出路径: 评论采集及打标数据_{ASIN}.csv"""
        project_dir = self._get_project_dir(asin)
        return project_dir / f"评论采集及打标数据_{asin}.csv"

    def get_html_path(self, asin: str) -> Path:
        """获取 HTML 报告输出路径: 可视化洞察报告_{ASIN}.html"""
        project_dir = self._get_project_dir(asin)
        return project_dir / f"可视化洞察报告_{asin}.html"

    def get_md_path(self, asin: str) -> Path:
        """获取 Markdown 洞察输出路径: 分析洞察报告_{ASIN}.md"""
        project_dir = self._get_project_dir(asin)
        return project_dir / f"分析洞察报告_{asin}.md"


def mask_api_key(key: str) -> str:
    """屏蔽API Key，只显示后4位

    Args:
        key: API Key字符串

    Returns:
        屏蔽后的字符串，格式为 ********1234

    Examples:
        >>> mask_api_key("AIzaSyD1234567890")
        '********7890'
        >>> mask_api_key("")
        '***'
        >>> mask_api_key("short")
        '***'
    """
    if not key or len(key) < 8:
        return "***"
    return f"{'*' * 8}{key[-4:]}"


# 全局配置实例
config = Config()

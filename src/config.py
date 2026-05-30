"""
配置管理模块 V2.0 — Agent 原生版

重大变更：
- 打标阶段改为 Prompt Router，宿主 Agent 直接执行，不再依赖 subprocess CLI
- 新增数据接入层配置（Sorftime 平台）
- 新增可视化模板系统配置
- 新增飞书同步配置
- 新增图表引擎配置
- 统一使用 CLI 引擎，不再支持 Gemini API
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class Config:
    """全局配置类 V2.0 - Agent 原生版"""

    # ==================== 项目路径配置 ====================
    PROJECT_ROOT: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    # 输出目录: 支持环境变量 OUTPUT_DIR 或命令行参数 --output-dir
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./output")))
    REFERENCES_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "references")
    ASSETS_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "assets")
    DATA_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")

    # ==================== CLI 引擎配置 ====================
    # 支持 claude / opencode 两种 CLI 引擎
    # claude  → subprocess: claude --print --dangerously-skip-permissions <prompt>
    # opencode → subprocess: opencode run <prompt>
    # 未指定时自动探测: 优先 claude，其次 opencode
    # V2.0 备注：打标阶段不再使用 CLI，由宿主 Agent 直接执行
    #            CLI 引擎仅用于洞察报告和 HTML 看板的生成
    CLI_ENGINE: str = ""  # 可选: claude / opencode / 留空自动探测
    CLAUDE_CLI_CMD: str = "claude"
    OPENCODE_CLI_CMD: str = "opencode"
    # CLI 调用超时时间（秒）- 从环境变量读取，默认 600 秒
    CLI_TIMEOUT: int = int(os.getenv("CLI_TIMEOUT", "600"))

    # ==================== V2.0: 数据接入配置 ====================
    DATA_SOURCE: str = "csv"  # 可选: csv / sorftime
    SORFTIME_API_KEY: str = os.getenv("SORFTIME_API_KEY", "")
    SORFTIME_MODE: str = "mcp"  # 可选: mcp / api / cli
    SORFTIME_BASE_URL: str = "https://mcp.sorftime.com"
    SORFTIME_MAX_REVIEWS: int = 100  # Sorftime 单次最多返回 100 条

    # ==================== V2.0: 可视化模板配置 ====================
    TEMPLATE_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "templates")
    DEFAULT_TEMPLATE: str = "premium-gold"  # 默认模板名称

    # ==================== V2.0: 飞书同步配置 ====================
    FEISHU_SYNC: bool = False  # 是否同步到飞书（用户选择）
    LARK_CLI_CMD: str = "lark-cli"  # 飞书 CLI 命令名

    # ==================== V2.0: 图表引擎配置 ====================
    CHART_ENGINE: str = "chartjs"  # 可选: chartjs / echarts
    CHART_COLOR_PALETTE: str = "premium-gold"  # 颜色主题

    # ==================== V2.0: Prompt 模板配置 ====================
    PROMPTS_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "prompts")
    INSIGHTS_CHAPTERS: str = "all"  # 可选: all / 自定义章节编号列表（如 "1,2,3,9,10"）

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
    # 最大并发子进程数（调用 claude -p）- 从环境变量读取，默认 4
    MAX_CONCURRENT_AGENTS: int = int(os.getenv("MAX_CONCURRENT", "4"))

    # ==================== 快速模式配置 ====================
    QUICK_MODE_MAX_REVIEWS: int = 30  # 快速模式默认获取评论数

    # ==================== 报告生成配置 ====================
    INSIGHTS_FORMAT: str = "txt"  # 可选: md / txt
    HTML_CREATOR_NAME: str = os.getenv("HTML_CREATOR_NAME", "Buluu@新西楼")

    def __post_init__(self):
        """初始化后验证"""
        # 确保输出目录存在
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 并发上限保护：超过 8 可能导致系统资源不足或 CLI rate limit
        MAX_CONCURRENT_CAP = 8
        if self.MAX_CONCURRENT_AGENTS > MAX_CONCURRENT_CAP:
            print(f"⚠️  并发数 {self.MAX_CONCURRENT_AGENTS} 超过上限 {MAX_CONCURRENT_CAP}，已自动调整为 {MAX_CONCURRENT_CAP}")
            self.MAX_CONCURRENT_AGENTS = MAX_CONCURRENT_CAP

        # V2.0: CLI 引擎不再是必须的（打标由宿主 Agent 执行）
        # 仅在洞察报告和 HTML 看板生成时才需要 CLI
        import shutil
        env_engine = os.getenv("CLI_ENGINE", "").lower()
        if env_engine in ("claude", "opencode"):
            self.CLI_ENGINE = env_engine

        if not self.CLI_ENGINE:
            # 自动探测: 优先 claude，其次 opencode，找不到也不报错
            if shutil.which(self.CLAUDE_CLI_CMD):
                self.CLI_ENGINE = "claude"
            elif shutil.which(self.OPENCODE_CLI_CMD):
                self.CLI_ENGINE = "opencode"
            else:
                # V2.0: 不再强制要求 CLI，但记录警告
                self.CLI_ENGINE = "none"

    @property
    def cli_cmd(self) -> str:
        """获取当前 CLI 引擎的命令名"""
        return self.OPENCODE_CLI_CMD if self.CLI_ENGINE == "opencode" else self.CLAUDE_CLI_CMD

    def build_cli_cmd(self, prompt: str) -> list:
        """构建 CLI 调用命令（统一入口）

        自动解析绝对路径并根据当前引擎类型构建正确的命令参数。
        V2.0: 当引擎为 "none" 时抛出 RuntimeError（仅洞察报告/看板生成需要 CLI）

        Args:
            prompt: 要传递给 CLI 的提示词

        Returns:
            命令列表，可直接传递给 subprocess.run()

        Raises:
            RuntimeError: 当 CLI 不可用时
        """
        import shutil

        if self.CLI_ENGINE == "none":
            raise RuntimeError(
                "❌ 当前无可用的 CLI 引擎。洞察报告和 HTML 看板生成需要 CLI。\n"
                "请安装 Claude Code 或 OpenCode 并加入 PATH"
            )

        cli_path = shutil.which(self.cli_cmd)
        if not cli_path:
            raise RuntimeError(
                f"❌ 找不到 CLI 引擎: {self.cli_cmd}\n"
                f"请确保已安装并加入 PATH"
            )

        if self.CLI_ENGINE == "opencode":
            return [cli_path, "run", prompt]
        else:
            return [cli_path, "--print", "--dangerously-skip-permissions", prompt]

    # ==================== V2.0: 新增方法 ====================

    def check_lark_cli(self) -> bool:
        """检查飞书 CLI 是否可用"""
        import shutil
        return shutil.which(self.LARK_CLI_CMD) is not None

    def check_sorftime_config(self) -> bool:
        """检查 Sorftime 配置是否可用"""
        return bool(self.SORFTIME_API_KEY)

    def list_templates(self) -> list:
        """列出可用的可视化模板"""
        if not self.TEMPLATE_DIR.exists():
            return []
        templates = []
        for d in sorted(self.TEMPLATE_DIR.iterdir()):
            if d.is_dir() and (d / "dashboard.html").exists():
                templates.append({
                    "name": d.name,
                    "path": str(d / "dashboard.html")
                })
        return templates

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


# 全局配置实例
config = Config()

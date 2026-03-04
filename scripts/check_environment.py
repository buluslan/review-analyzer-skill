#!/usr/bin/env python3
"""
环境检查脚本
检查Python版本、依赖库、CLI工具和配置文件
"""

import sys
import subprocess
import importlib
import os
from pathlib import Path
from typing import List, Tuple, Dict

# ANSI颜色代码
class Colors:
    """终端颜色代码"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 定义检查项目
class EnvironmentChecker:
    """环境检查器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.recommendations: List[str] = []

    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

    def print_section(self, title: str):
        """打印章节标题"""
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}▶ {title}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}\n")

    def check_python_version(self) -> Tuple[bool, str]:
        """检查Python版本"""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        # 推荐版本列表
        recommended_versions = [(3, 11), (3, 10), (3, 12)]

        is_recommended = (version.major, version.minor) in recommended_versions
        is_supported = version.major == 3 and version.minor >= 9

        if version.major == 3 and version.minor == 9 and version.micro == 6:
            status = f"{Colors.WARNING}⚠️  Python 版本: {version_str} (已过EOL，强烈建议升级){Colors.ENDC}"
            self.recommendations.append(
                "您正在使用Python 3.9.6，该版本已于2024年10月停止支持。\n"
                "   强烈建议升级到 Python 3.11 或更高版本。\n"
                "   运行以下命令查看升级指南:\n"
                "   cat docs/PYTHON_UPGRADE.md"
            )
            return False, status
        elif is_recommended:
            status = f"{Colors.OKGREEN}✅ Python 版本: {version_str} (推荐){Colors.ENDC}"
            return True, status
        elif is_supported:
            status = f"{Colors.WARNING}⚠️  Python 版本: {version_str} (支持但非推荐){Colors.ENDC}"
            return True, status
        else:
            status = f"{Colors.FAIL}❌ Python 版本: {version_str} (不支持){Colors.ENDC}"
            self.issues.append(
                f"Python {version_str} 不受支持。\n"
                f"   本项目需要 Python 3.9 或更高版本。\n"
                f"   推荐使用 Python 3.11 或更高版本。"
            )
            return False, status

    def check_dependencies(self) -> List[Dict[str, str]]:
        """检查依赖库"""
        requirements = [
            ('apify', 'apify-client', '1.8.1'),
            ('requests', 'requests', '2.32.3'),
            ('bs4', 'beautifulsoup4', '4.12.3'),
            ('google.generativeai', 'google-generativeai', '0.8.4'),
            ('pandas', 'pandas', '2.2.3'),
            ('jinja2', 'jinja2', '3.1.4'),
            ('dotenv', 'python-dotenv', '1.0.1'),
            ('tqdm', 'tqdm', '4.66.4'),
        ]

        results = []
        for module_name, package_name, expected_version in requirements:
            try:
                module = importlib.import_module(module_name)
                actual_version = getattr(module, '__version__', 'unknown')

                # 简单版本比较（仅比较主版本号）
                expected_major = expected_version.split('.')[0]
                actual_major = actual_version.split('.')[0]

                if actual_version == expected_version:
                    status = f"{Colors.OKGREEN}✅{Colors.ENDC}"
                    level = "ok"
                elif actual_major == expected_major:
                    status = f"{Colors.WARNING}⚠️ {Colors.ENDC}"
                    level = "warning"
                    self.warnings.append(
                        f"{package_name}: 版本 {actual_version} (期望: {expected_version})"
                    )
                else:
                    status = f"{Colors.WARNING}⚠️ {Colors.ENDC}"
                    level = "warning"
                    self.warnings.append(
                        f"{package_name}: 版本 {actual_version} (期望: {expected_version})"
                    )

                results.append({
                    'package': package_name,
                    'expected': expected_version,
                    'actual': actual_version,
                    'status': status,
                    'level': level
                })

            except ImportError:
                results.append({
                    'package': package_name,
                    'expected': expected_version,
                    'actual': '未安装',
                    'status': f"{Colors.FAIL}❌{Colors.ENDC}",
                    'level': 'error'
                })
                self.issues.append(f"缺少依赖: {package_name}")

        return results

    def check_claude_cli(self) -> Tuple[bool, str]:
        """检查Claude CLI"""
        try:
            result = subprocess.run(
                ['claude', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1]
                return True, f"{Colors.OKGREEN}✅ Claude CLI: 已安装 (版本: {version}){Colors.ENDC}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        self.recommendations.append(
            "Claude CLI 未安装或不可用。\n"
            "   CLI深度模式需要Claude CLI才能运行。\n"
            "   安装命令: npm install -g @anthropic-ai/claude-code\n"
            "   或仅使用Gemini快速模式（需要API Key）。"
        )
        return False, f"{Colors.WARNING}⚠️  Claude CLI: 未安装（CLI深度模式需要）{Colors.ENDC}"

    def check_env_file(self) -> Tuple[bool, str]:
        """检查.env文件"""
        env_file = self.project_root / '.env'
        env_example = self.project_root / '.env.example'

        if not env_file.exists():
            if env_example.exists():
                status = f"{Colors.WARNING}⚠️  .env: 未配置 (存在 .env.example){Colors.ENDC}"
                self.recommendations.append(
                    "未找到.env配置文件。\n"
                    "   复制示例配置: cp .env.example .env\n"
                    "   然后编辑.env文件添加您的API Key。"
                )
            else:
                status = f"{Colors.WARNING}⚠️  .env: 未配置{Colors.ENDC}"
            return False, status

        # 检查关键配置
        env_content = env_file.read_text()
        has_gemini_key = 'GEMINI_API_KEY' in env_content and len(env_content.split('GEMINI_API_KEY=')[1].split('\n')[0].strip()) > 10

        if has_gemini_key:
            return True, f"{Colors.OKGREEN}✅ .env: 已配置 (GEMINI_API_KEY){Colors.ENDC}"
        else:
            self.recommendations.append(
                "GEMINI_API_KEY 未配置或为空。\n"
                "   获取API Key: https://aistudio.google.com/app/apikey\n"
                "   然后在.env文件中添加: GEMINI_API_KEY=your_key_here"
            )
            return False, f"{Colors.WARNING}⚠️  .env: GEMINI_API_KEY 未配置{Colors.ENDC}"

    def check_project_structure(self) -> List[Tuple[bool, str]]:
        """检查项目结构"""
        required_paths = [
            ('main.py', '主入口文件'),
            ('requirements.txt', '依赖文件'),
            ('src/config.py', '配置模块'),
            ('src/prompts/templates.py', '提示词模板'),
            ('assets/report.html', 'HTML报告模板'),
            ('docs/QUICKSTART.md', '快速开始文档'),
        ]

        results = []
        for path, description in required_paths:
            full_path = self.project_root / path
            if full_path.exists():
                results.append((True, f"{Colors.OKGREEN}✅{Colors.ENDC} {description}"))
            else:
                results.append((False, f"{Colors.FAIL}❌{Colors.ENDC} {description} 缺失"))
                self.issues.append(f"项目文件缺失: {path}")

        return results

    def print_summary(self):
        """打印总结"""
        self.print_header("环境检查报告")

        # Python版本检查
        self.print_section("1. Python 版本检查")
        python_ok, python_status = self.check_python_version()
        print(python_status)

        # 依赖检查
        self.print_section("2. 依赖库检查")
        deps = self.check_dependencies()
        for dep in deps:
            print(f"{dep['status']} {dep['package']:<25} 期望: {dep['expected']:<10} 实际: {dep['actual']}")

        # Claude CLI检查
        self.print_section("3. CLI 工具检查")
        claude_ok, claude_status = self.check_claude_cli()
        print(claude_status)

        # 配置文件检查
        self.print_section("4. 配置文件检查")
        env_ok, env_status = self.check_env_file()
        print(env_status)

        # 项目结构检查
        self.print_section("5. 项目结构检查")
        structure_checks = self.check_project_structure()
        for ok, status in structure_checks:
            print(status)

        # 打印问题和建议
        if self.issues:
            self.print_section("❌ 发现的问题")
            for i, issue in enumerate(self.issues, 1):
                print(f"{Colors.FAIL}{i}. {issue}{Colors.ENDC}\n")

        if self.warnings:
            self.print_section("⚠️  警告信息")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{Colors.WARNING}{i}. {warning}{Colors.ENDC}\n")

        if self.recommendations:
            self.print_section("💡 改进建议")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"{Colors.OKCYAN}{i}. {rec}{Colors.ENDC}\n")

        # 总体状态
        self.print_header("检查完成")

        all_ok = python_ok and claude_ok and env_ok and all(ok for ok, _ in structure_checks)

        if all_ok and not self.issues and not self.warnings:
            print(f"{Colors.OKGREEN}{Colors.BOLD}✅ 恭喜！您的环境配置完美！{Colors.ENDC}\n")
            print("您可以开始使用项目了：")
            print(f"  python main.py examples/reviews_sample.csv")
        elif not self.issues:
            print(f"{Colors.OKGREEN}{Colors.BOLD}✅ 环境基本就绪，但有一些改进建议{Colors.ENDC}\n")
            print("项目应该可以正常运行，但建议查看上面的改进建议。")
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}❌ 发现问题需要解决{Colors.ENDC}\n")
            print("请按照上述说明解决问题后再次运行检查。")
            print(f"\n查看升级指南：")
            print(f"  cat docs/PYTHON_UPGRADE.md")

        print()

    def run(self):
        """运行环境检查"""
        try:
            self.print_summary()
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}检查已取消{Colors.ENDC}")
            sys.exit(1)
        except Exception as e:
            print(f"\n\n{Colors.FAIL}检查过程中发生错误: {e}{Colors.ENDC}")
            sys.exit(1)


def main():
    """主函数"""
    checker = EnvironmentChecker()
    checker.run()


if __name__ == '__main__':
    main()

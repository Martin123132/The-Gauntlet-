from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata, util
from pathlib import Path
import json
import platform
import sys

from .ocr import OcrReadinessReport, collect_ocr_readiness
from .workspace import workspace_runs_dir


APP_VERSION = "v0.21.0-dev"
DIAGNOSTIC_STATUSES = ("ok", "warn", "fail")
REQUIRED_DEPENDENCIES = (
    ("streamlit", "streamlit"),
    ("pypdf", "pypdf"),
    ("python-docx", "docx"),
)
REQUIRED_PUBLIC_FILES = (
    "Start-Gauntlet.bat",
    "requirements.txt",
    "app.py",
    "README.md",
)


@dataclass(frozen=True)
class DiagnosticItem:
    name: str
    status: str
    detail: str
    recovery: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SystemCheckReport:
    app_version: str
    generated_at: str
    python_version: str
    python_executable: str
    repo_path: str
    workspace_path: str
    launcher_log_path: str
    ocr_readiness: OcrReadinessReport
    items: tuple[DiagnosticItem, ...]

    @property
    def overall_status(self) -> str:
        statuses = {item.status for item in self.items}
        if "fail" in statuses:
            return "fail"
        if "warn" in statuses:
            return "warn"
        return "ok"

    @property
    def status_counts(self) -> dict[str, int]:
        return {status: sum(1 for item in self.items if item.status == status) for status in DIAGNOSTIC_STATUSES}

    def to_dict(self) -> dict:
        return {
            "app_version": self.app_version,
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "status_counts": self.status_counts,
            "python_version": self.python_version,
            "python_executable": self.python_executable,
            "repo_path": self.repo_path,
            "workspace_path": self.workspace_path,
            "launcher_log_path": self.launcher_log_path,
            "ocr_readiness": self.ocr_readiness.to_dict(),
            "items": [item.to_dict() for item in self.items],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        lines = [
            "# The Gauntlet System Check",
            "",
            f"- App version: {self.app_version}",
            f"- Generated: {self.generated_at}",
            f"- Overall status: {self.overall_status.upper()}",
            f"- Python: {self.python_version}",
            f"- Python executable: `{self.python_executable}`",
            f"- Repo path: `{self.repo_path}`",
            f"- Workspace path: `{self.workspace_path}`",
            f"- Launcher log: `{self.launcher_log_path}`",
            f"- OCR readiness: **{self.ocr_readiness.status}**",
            "",
            "## Checks",
            "",
        ]
        for item in self.items:
            lines.append(f"### {item.name}")
            lines.append(f"- Status: **{item.status.upper()}**")
            lines.append(f"- Detail: {item.detail}")
            if item.recovery:
                lines.append(f"- Recovery: {item.recovery}")
            lines.append("")
        lines.extend(
            [
                "## Privacy",
                "",
                "This diagnostic report lists local paths, dependency status, and setup state. It does not include uploaded paper files, report contents, API keys, or full launcher logs.",
                "",
            ]
        )
        return "\n".join(lines)


def collect_system_check(
    repo_path: str | Path | None = None,
    workspace_path: str | Path | None = None,
) -> SystemCheckReport:
    repo = Path(repo_path).resolve() if repo_path is not None else Path(__file__).resolve().parents[1]
    workspace = Path(workspace_path).resolve() if workspace_path is not None else workspace_runs_dir().resolve()
    launcher_log = repo / ".gauntlet" / "logs" / "Start-Gauntlet.log"
    ocr_readiness = collect_ocr_readiness()
    items: list[DiagnosticItem] = []
    items.append(python_version_check())
    items.append(virtual_environment_check())
    items.extend(dependency_checks())
    items.extend(public_file_checks(repo))
    items.append(workspace_check(workspace))
    items.append(launcher_log_check(launcher_log))
    items.append(optional_ocr_check(ocr_readiness))
    items.append(optional_ai_check(repo))
    return SystemCheckReport(
        app_version=APP_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        python_version=platform.python_version(),
        python_executable=sys.executable,
        repo_path=str(repo),
        workspace_path=str(workspace),
        launcher_log_path=str(launcher_log),
        ocr_readiness=ocr_readiness,
        items=tuple(items),
    )


def python_version_check() -> DiagnosticItem:
    version_text = platform.python_version()
    if sys.version_info >= (3, 10):
        return DiagnosticItem("Python 3.10+", "ok", f"Running Python {version_text}.")
    return DiagnosticItem(
        "Python 3.10+",
        "fail",
        f"Running Python {version_text}, which is too old for the public launcher path.",
        "Install Python 3.10 or newer, then run Start-Gauntlet.bat again.",
    )


def virtual_environment_check() -> DiagnosticItem:
    if sys.prefix != sys.base_prefix:
        return DiagnosticItem("Virtual environment", "ok", f"Running inside virtual environment: {sys.prefix}")
    return DiagnosticItem(
        "Virtual environment",
        "warn",
        "The app is running outside a Python virtual environment.",
        "GitHub ZIP users should start with Start-Gauntlet.bat so dependencies stay local to .venv.",
    )


def dependency_checks() -> tuple[DiagnosticItem, ...]:
    items: list[DiagnosticItem] = []
    for package_name, import_name in REQUIRED_DEPENDENCIES:
        if util.find_spec(import_name) is None:
            items.append(
                DiagnosticItem(
                    f"Dependency: {package_name}",
                    "fail",
                    f"Python cannot import {import_name}.",
                    "Run Start-Gauntlet.bat again or install requirements.txt inside .venv.",
                )
            )
            continue
        try:
            version = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            version = "installed"
        items.append(DiagnosticItem(f"Dependency: {package_name}", "ok", f"{package_name} {version} is available."))
    return tuple(items)


def public_file_checks(repo: Path) -> tuple[DiagnosticItem, ...]:
    items: list[DiagnosticItem] = []
    for relative_path in REQUIRED_PUBLIC_FILES:
        path = repo / relative_path
        if path.exists():
            items.append(DiagnosticItem(f"Required file: {relative_path}", "ok", f"Found at {path}."))
        else:
            items.append(
                DiagnosticItem(
                    f"Required file: {relative_path}",
                    "fail",
                    f"Missing from repo path {repo}.",
                    "Re-download the GitHub ZIP or restore the missing file from the repository.",
                )
            )
    return tuple(items)


def workspace_check(workspace: Path) -> DiagnosticItem:
    if workspace.exists():
        return DiagnosticItem("Local workspace", "ok", f"Workspace directory exists at {workspace}.")
    if workspace.parent.exists():
        return DiagnosticItem(
            "Local workspace",
            "warn",
            f"Workspace directory has not been created yet: {workspace}.",
            "Run a sample or paper analysis; The Gauntlet will create it when saving the first run.",
        )
    return DiagnosticItem(
        "Local workspace",
        "warn",
        f"Workspace parent folder does not exist yet: {workspace.parent}.",
        "Run a sample analysis from the Summary page to create the local workspace.",
    )


def launcher_log_check(launcher_log: Path) -> DiagnosticItem:
    if not launcher_log.exists():
        return DiagnosticItem(
            "Launcher log",
            "warn",
            f"No launcher log found at {launcher_log}.",
            "Start the app with Start-Gauntlet.bat to create a troubleshooting log.",
        )
    size_kb = launcher_log.stat().st_size / 1024
    modified = datetime.fromtimestamp(launcher_log.stat().st_mtime).isoformat(timespec="seconds")
    return DiagnosticItem("Launcher log", "ok", f"Found {launcher_log} ({size_kb:.1f} KB, modified {modified}).")


def optional_ocr_check(readiness: OcrReadinessReport) -> DiagnosticItem:
    if readiness.status == "available":
        return DiagnosticItem("Optional OCR readiness", "ok", readiness.detail, readiness.recovery)
    return DiagnosticItem("Optional OCR readiness", "warn", readiness.detail, readiness.recovery)


def optional_ai_check(repo: Path) -> DiagnosticItem:
    requirements_ai = repo / "requirements-ai.txt"
    if requirements_ai.exists():
        return DiagnosticItem(
            "Optional AI requirements",
            "ok",
            "requirements-ai.txt is present. Optional Gemini/OpenAI/Anthropic refinement remains separate from the default checker.",
        )
    return DiagnosticItem(
        "Optional AI requirements",
        "warn",
        "requirements-ai.txt is missing.",
        "Restore requirements-ai.txt only if you want optional AI refinement support.",
    )

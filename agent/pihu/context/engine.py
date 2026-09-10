import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class EnvironmentContext(BaseModel):
    os: str
    shell: str
    cwd: str
    datetime_utc: str
    timezone_local: str

class ProjectContext(BaseModel):
    project_root: str
    project_type: str
    git_branch: Optional[str] = None
    has_git: bool = False

class FullContext(BaseModel):
    environment: EnvironmentContext
    project: ProjectContext
    session_id: Optional[str] = None
    custom_facts: Dict[str, Any] = Field(default_factory=dict)

class ContextEngine:
    """Gathers selective Environment, Project, Session, and Persistent Context."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()

    def get_environment_context(self) -> EnvironmentContext:
        now = datetime.now()
        local_tz = now.astimezone().tzname() or "Local"
        return EnvironmentContext(
            os=sys.platform,
            shell=os.getenv("SHELL", "zsh"),
            cwd=str(Path.cwd()),
            datetime_utc=datetime.now(timezone.utc).isoformat(),
            timezone_local=local_tz
        )

    def get_project_context(self) -> ProjectContext:
        root = self.project_root
        git_branch = None
        has_git = (root / ".git").exists()

        if has_git:
            try:
                res = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if res.returncode == 0:
                    git_branch = res.stdout.strip()
            except Exception:
                pass

        # Detect project type
        project_types = []
        if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
            project_types.append("Python")
        if (root / "go.mod").exists():
            project_types.append("Go")
        if (root / "package.json").exists():
            project_types.append("Node.js")

        p_type = ", ".join(project_types) if project_types else "Generic"

        return ProjectContext(
            project_root=str(root),
            project_type=p_type,
            git_branch=git_branch,
            has_git=has_git
        )

    def assemble_context(self, session_id: Optional[str] = None) -> FullContext:
        return FullContext(
            environment=self.get_environment_context(),
            project=self.get_project_context(),
            session_id=session_id
        )

    def render_system_context_prompt(self, session_id: Optional[str] = None) -> str:
        ctx = self.assemble_context(session_id=session_id)
        lines = [
            "--- ENVIRONMENT & PROJECT CONTEXT ---",
            f"Operating System: {ctx.environment.os}",
            f"Shell: {ctx.environment.shell}",
            f"Working Directory: {ctx.environment.cwd}",
            f"Current Date/Time (UTC): {ctx.environment.datetime_utc}",
            f"Local Timezone: {ctx.environment.timezone_local}",
            f"Project Root: {ctx.project.project_root}",
            f"Project Type: {ctx.project.project_type}",
        ]
        if ctx.project.git_branch:
            lines.append(f"Git Branch: {ctx.project.git_branch}")
        lines.append("-------------------------------------")
        return "\n".join(lines)

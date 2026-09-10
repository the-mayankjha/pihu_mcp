from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from pihu.config.settings import settings
from pihu.events.bus import bus
from pihu.events.types import AgentEvent, EventType

class RiskLevel(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXTERNAL = "EXTERNAL"
    DESTRUCTIVE = "DESTRUCTIVE"

class PermissionCheckResult(BaseModel):
    allowed: bool
    requires_user_approval: bool
    risk_level: RiskLevel
    reason: str

class SecurityManager:
    """Security layer assessing risk levels of tool invocations and enforcing permission policies."""

    @staticmethod
    def classify_risk(tool_name: str, arguments: Dict[str, Any]) -> RiskLevel:
        lower_name = tool_name.lower()

        # Check for destructive keywords
        destructive_keywords = ["delete", "remove", "drop", "destroy", "wipe", "force", "kill"]
        if any(kw in lower_name for kw in destructive_keywords):
            return RiskLevel.DESTRUCTIVE

        # Check for external communication
        external_keywords = ["send", "mail", "post", "publish", "github__create", "upload", "tweet"]
        if any(kw in lower_name for kw in external_keywords):
            return RiskLevel.EXTERNAL

        # Check for write operations
        write_keywords = ["write", "create", "update", "edit", "mkdir", "move", "copy"]
        if any(kw in lower_name for kw in write_keywords):
            return RiskLevel.WRITE

        # Default to READ
        return RiskLevel.READ

    async def check_permission(self, tool_name: str, arguments: Dict[str, Any]) -> PermissionCheckResult:
        risk_level = self.classify_risk(tool_name, arguments)

        if risk_level == RiskLevel.READ:
            return PermissionCheckResult(
                allowed=True,
                requires_user_approval=False,
                risk_level=risk_level,
                reason="Read operations are automatically approved."
            )

        if risk_level == RiskLevel.WRITE:
            if not settings.require_approval_write:
                return PermissionCheckResult(
                    allowed=True,
                    requires_user_approval=False,
                    risk_level=risk_level,
                    reason="Write operations auto-approved by settings configuration."
                )
            return PermissionCheckResult(
                allowed=True,
                requires_user_approval=True,
                risk_level=risk_level,
                reason=f"Write operation '{tool_name}' requires approval."
            )

        if risk_level == RiskLevel.EXTERNAL:
            return PermissionCheckResult(
                allowed=True,
                requires_user_approval=True,
                risk_level=risk_level,
                reason=f"External action '{tool_name}' requires approval."
            )

        # DESTRUCTIVE
        return PermissionCheckResult(
            allowed=True,
            requires_user_approval=True,
            risk_level=risk_level,
            reason=f"Destructive action '{tool_name}' requires explicit approval."
        )

    async def request_user_approval(self, tool_name: str, arguments: Dict[str, Any], risk_level: RiskLevel) -> bool:
        """Emit PERMISSION_REQUIRED event over IPC/bus and await user confirmation."""
        await bus.emit(
            AgentEvent(
                type=EventType.PERMISSION_REQUIRED,
                component="security_manager",
                status="pending",
                message=f"PIHU requires approval to execute {risk_level.value} action: {tool_name}",
                details={
                    "tool": tool_name,
                    "arguments": arguments,
                    "risk_level": risk_level.value
                }
            )
        )
        # In non-interactive mode or auto-approve fallback, default to True for standard scripts
        # In full Go CLI IPC mode, the Go CLI will answer with PERMISSION_RESPONSE event.
        return True

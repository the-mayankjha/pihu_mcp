import pytest
from pihu.security.permissions import SecurityManager, RiskLevel

@pytest.mark.asyncio
async def test_risk_classification():
    sec = SecurityManager()

    assert sec.classify_risk("files__read_file", {}) == RiskLevel.READ
    assert sec.classify_risk("files__write_file", {}) == RiskLevel.WRITE
    assert sec.classify_risk("github__create_issue", {}) == RiskLevel.EXTERNAL
    assert sec.classify_risk("system__delete_file", {}) == RiskLevel.DESTRUCTIVE

@pytest.mark.asyncio
async def test_check_permission_read():
    sec = SecurityManager()
    res = await sec.check_permission("files__read_file", {})

    assert res.allowed is True
    assert res.requires_user_approval is False
    assert res.risk_level == RiskLevel.READ

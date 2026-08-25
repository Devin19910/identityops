from identityops.governance.risk_rules import classify_scopes
from identityops.models import RiskLevel


def test_low_risk_scopes():
    risk, flagged = classify_scopes(["openid", "profile", "User.Read"])
    assert risk == RiskLevel.LOW
    assert flagged == []


def test_high_risk_scope_triggers_high():
    risk, flagged = classify_scopes(["openid", "Mail.ReadWrite"])
    assert risk == RiskLevel.HIGH
    assert "Mail.ReadWrite" in flagged


def test_unknown_scope_is_medium_not_low():
    risk, flagged = classify_scopes(["openid", "SomeVendor.CustomScope"])
    assert risk == RiskLevel.MEDIUM
    assert "SomeVendor.CustomScope" in flagged

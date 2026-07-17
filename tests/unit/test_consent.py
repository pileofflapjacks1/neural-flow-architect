"""Consent manager tests."""

from neural_flow_architect.privacy.consent import ConsentManager, ConsentScope


def test_default_grants() -> None:
    c = ConsentManager()
    assert c.allows(ConsentScope.ACQUIRE)
    assert c.allows(ConsentScope.AGENT_ACT)
    assert not c.allows(ConsentScope.PERSIST_RAW)
    assert not c.allows(ConsentScope.OPTIONAL_LLM)


def test_revoke() -> None:
    c = ConsentManager()
    c.set(ConsentScope.AGENT_ACT, False)
    assert not c.allows(ConsentScope.AGENT_ACT)
    c.revoke_all()
    assert not c.allows(ConsentScope.ACQUIRE)

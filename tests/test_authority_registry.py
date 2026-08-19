from dataclasses import replace

from oma.authority import AuthorityContext, Capability
from oma.authority_registry import (
    AuthorityRegistryDecision,
    SQLiteAuthorityRegistry,
)


def context(**overrides):
    values = dict(
        authority_context_id="authority:v1",
        authority_epoch=1,
        now_epoch=1,
        trusted_issuers=frozenset({"root"}),
    )
    values.update(overrides)
    return AuthorityContext(**values)


def root(**overrides):
    values = dict(
        capability_id="root-cap",
        issuer="root",
        holder="agent",
        actions=frozenset({"commit", "read"}),
        targets=frozenset({"subject-1"}),
        scopes=frozenset({"repo"}),
        authority_epoch=1,
        not_before_epoch=0,
        expires_epoch=10,
        parent_capability_id=None,
    )
    values.update(overrides)
    return Capability(**values)


def child(**overrides):
    values = dict(
        capability_id="child-cap",
        issuer="agent",
        holder="worker",
        actions=frozenset({"read"}),
        targets=frozenset({"subject-1"}),
        scopes=frozenset({"repo"}),
        authority_epoch=1,
        not_before_epoch=0,
        expires_epoch=9,
        parent_capability_id="root-cap",
    )
    values.update(overrides)
    return Capability(**values)


def test_bootstrap_persists_root_across_reopen(tmp_path):
    path = tmp_path / "oma.db"
    registry = SQLiteAuthorityRegistry(path)
    assert registry.initialize_context(context(), (root(),)).decision is AuthorityRegistryDecision.WRITTEN
    assert SQLiteAuthorityRegistry(path).get(context()) == (root(),)


def test_duplicate_context_bootstrap_conflicts(tmp_path):
    registry = SQLiteAuthorityRegistry(tmp_path / "oma.db")
    assert registry.initialize_context(context(), (root(),)).decision is AuthorityRegistryDecision.WRITTEN
    assert registry.initialize_context(context(), (root(),)).decision is AuthorityRegistryDecision.CONFLICT


def test_untrusted_root_cannot_bootstrap(tmp_path):
    registry = SQLiteAuthorityRegistry(tmp_path / "oma.db")
    result = registry.initialize_context(context(), (root(issuer="evil"),))
    assert result.decision is AuthorityRegistryDecision.BLOCK


def test_post_bootstrap_root_issue_is_forbidden(tmp_path):
    registry = SQLiteAuthorityRegistry(tmp_path / "oma.db")
    registry.initialize_context(context(), (root(),))
    result = registry.issue(
        context(),
        root(capability_id="forged-root", holder="attacker"),
    )
    assert result.decision is AuthorityRegistryDecision.BLOCK
    assert result.reasons == ("post_bootstrap_root_issue_forbidden",)


def test_valid_subset_delegation_is_persisted(tmp_path):
    registry = SQLiteAuthorityRegistry(tmp_path / "oma.db")
    registry.initialize_context(context(), (root(),))
    result = registry.issue(context(), child())
    assert result.decision is AuthorityRegistryDecision.WRITTEN
    assert set(registry.get(context())) == {root(), child()}


def test_delegation_escalation_is_blocked(tmp_path):
    registry = SQLiteAuthorityRegistry(tmp_path / "oma.db")
    registry.initialize_context(context(), (root(),))
    result = registry.issue(
        context(),
        child(actions=frozenset({"delete"})),
    )
    assert result.decision is AuthorityRegistryDecision.BLOCK
    assert registry.get(context()) == (root(),)


def test_context_policy_change_cannot_read_registry(tmp_path):
    registry = SQLiteAuthorityRegistry(tmp_path / "oma.db")
    registry.initialize_context(context(), (root(),))
    changed = replace(context(), trusted_issuers=frozenset({"other"}))
    assert registry.get(changed) is None


def test_registry_rejects_ambiguous_newline_identifier(tmp_path):
    registry = SQLiteAuthorityRegistry(tmp_path / "oma.db")
    result = registry.initialize_context(
        context(),
        (root(capability_id="root\ncap"),),
    )
    assert result.decision is AuthorityRegistryDecision.BLOCK

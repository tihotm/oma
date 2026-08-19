from oma.authority import (
    AuthorityContext,
    AuthorityDecision,
    AuthorityRequest,
    Capability,
    evaluate_authority,
)


def ctx(**overrides):
    values = dict(
        authority_context_id="auth:1",
        authority_epoch=5,
        now_epoch=50,
        trusted_issuers=frozenset({"root"}),
    )
    values.update(overrides)
    return AuthorityContext(**values)


def cap(**overrides):
    values = dict(
        capability_id="cap:root",
        issuer="root",
        holder="supervisor",
        actions=frozenset({"VERIFY", "COMMIT"}),
        targets=frozenset({"subject:1"}),
        scopes=frozenset({"repo:oma"}),
        authority_epoch=5,
        not_before_epoch=1,
        expires_epoch=100,
        parent_capability_id=None,
    )
    values.update(overrides)
    return Capability(**values)


def req(**overrides):
    values = dict(
        actor="supervisor",
        action="COMMIT",
        target="subject:1",
        scope="repo:oma",
        capability_id="cap:root",
    )
    values.update(overrides)
    return AuthorityRequest(**values)


def test_valid_root_allows():
    assert evaluate_authority(ctx(), [cap()], req()).decision is AuthorityDecision.ALLOW


def test_unknown_capability_blocks():
    assert evaluate_authority(ctx(), [], req()).decision is AuthorityDecision.BLOCK


def test_untrusted_root_blocks():
    assert evaluate_authority(ctx(), [cap(issuer="evil")], req()).decision is AuthorityDecision.BLOCK


def test_root_self_authorization_blocks():
    assert evaluate_authority(ctx(), [cap(holder="root")], req(actor="root")).decision is AuthorityDecision.BLOCK


def test_actor_mismatch_blocks():
    assert evaluate_authority(ctx(), [cap()], req(actor="worker")).decision is AuthorityDecision.BLOCK


def test_action_not_authorized_blocks():
    assert evaluate_authority(ctx(), [cap()], req(action="DELETE")).decision is AuthorityDecision.BLOCK


def test_target_not_authorized_blocks():
    assert evaluate_authority(ctx(), [cap()], req(target="subject:2")).decision is AuthorityDecision.BLOCK


def test_scope_not_authorized_blocks():
    assert evaluate_authority(ctx(), [cap()], req(scope="repo:other")).decision is AuthorityDecision.BLOCK


def test_expired_capability_is_stale():
    assert evaluate_authority(ctx(now_epoch=101), [cap()], req()).decision is AuthorityDecision.STALE


def test_old_authority_epoch_is_stale():
    assert evaluate_authority(ctx(authority_epoch=6), [cap()], req()).decision is AuthorityDecision.STALE


def test_future_authority_epoch_blocks():
    assert evaluate_authority(ctx(authority_epoch=4), [cap()], req()).decision is AuthorityDecision.BLOCK


def test_not_yet_valid_blocks():
    assert evaluate_authority(ctx(now_epoch=0), [cap()], req()).decision is AuthorityDecision.BLOCK


def test_duplicate_capability_id_blocks():
    assert evaluate_authority(ctx(), [cap(), cap()], req()).decision is AuthorityDecision.BLOCK


def test_valid_delegation_allows():
    parent = cap()
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="worker",
        actions=frozenset({"VERIFY"}),
        parent_capability_id="cap:root",
        expires_epoch=80,
    )
    request = req(actor="worker", action="VERIFY", capability_id="cap:child")
    assert evaluate_authority(ctx(), [parent, child], request).decision is AuthorityDecision.ALLOW


def test_action_escalation_blocks():
    parent = cap(actions=frozenset({"VERIFY"}))
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="worker",
        actions=frozenset({"VERIFY", "COMMIT"}),
        parent_capability_id="cap:root",
    )
    assert evaluate_authority(ctx(), [parent, child], req(actor="worker", capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_target_escalation_blocks():
    parent = cap()
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="worker",
        targets=frozenset({"subject:1", "subject:2"}),
        parent_capability_id="cap:root",
    )
    assert evaluate_authority(ctx(), [parent, child], req(actor="worker", capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_scope_escalation_blocks():
    parent = cap()
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="worker",
        scopes=frozenset({"repo:oma", "repo:other"}),
        parent_capability_id="cap:root",
    )
    assert evaluate_authority(ctx(), [parent, child], req(actor="worker", capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_expiry_escalation_blocks():
    parent = cap(expires_epoch=80)
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="worker",
        parent_capability_id="cap:root",
        expires_epoch=90,
    )
    assert evaluate_authority(ctx(), [parent, child], req(actor="worker", capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_not_before_escalation_blocks():
    parent = cap(not_before_epoch=10)
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="worker",
        parent_capability_id="cap:root",
        not_before_epoch=5,
    )
    assert evaluate_authority(ctx(), [parent, child], req(actor="worker", capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_wrong_delegating_issuer_blocks():
    parent = cap()
    child = cap(
        capability_id="cap:child",
        issuer="other",
        holder="worker",
        parent_capability_id="cap:root",
    )
    assert evaluate_authority(ctx(), [parent, child], req(actor="worker", capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_self_delegation_blocks():
    parent = cap()
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="supervisor",
        parent_capability_id="cap:root",
    )
    assert evaluate_authority(ctx(), [parent, child], req(capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_missing_parent_blocks():
    child = cap(
        capability_id="cap:child",
        issuer="supervisor",
        holder="worker",
        parent_capability_id="missing",
    )
    assert evaluate_authority(ctx(), [child], req(actor="worker", capability_id="cap:child")).decision is AuthorityDecision.BLOCK


def test_capability_cycle_blocks():
    a = cap(capability_id="a", issuer="bholder", holder="aholder", parent_capability_id="b")
    b = cap(capability_id="b", issuer="aholder", holder="bholder", parent_capability_id="a")
    assert evaluate_authority(ctx(), [a, b], req(actor="aholder", capability_id="a")).decision is AuthorityDecision.BLOCK


def test_stale_precedes_request_permission_failure():
    assert evaluate_authority(ctx(now_epoch=101), [cap()], req(action="DELETE")).decision is AuthorityDecision.STALE

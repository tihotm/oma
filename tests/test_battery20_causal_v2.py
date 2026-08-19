from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope
from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def _scope_policy():
    return ScopePolicy(scope_policy_id="scope-v2", allowed_paths=("src",), forbidden_paths=("src/secret",), protected_roles=frozenset({"protected"}), review_roles=frozenset({"review"}))


def test_01_changed_transition_cannot_claim_untouched():
    assert evaluate_scope(_scope_policy(), (FileTransition("src/a.py", "before", "after", touched=False),)).decision is ScopeDecision.BLOCK


def test_02_hidden_touch_restore_is_accepted_when_caller_sets_untouched():
    assert evaluate_scope(_scope_policy(), (FileTransition("src/a.py", "same", "same", roles=frozenset({"protected"}), touched=False),)).decision is ScopeDecision.ALLOW


def test_03_omitted_protected_role_allows_changed_file():
    assert evaluate_scope(_scope_policy(), (FileTransition("src/a.py", "before", "after", roles=frozenset(), touched=True),)).decision is ScopeDecision.ALLOW


def test_04_forbidden_touch_restore_can_be_hidden_as_untouched():
    assert evaluate_scope(_scope_policy(), (FileTransition("src/secret/key.txt", "same", "same", touched=False),)).decision is ScopeDecision.ALLOW


def test_05_path_traversal_is_blocked():
    assert evaluate_scope(_scope_policy(), (FileTransition("src/../secret.txt", "a", "b"),)).decision is ScopeDecision.BLOCK


def _trust(epoch=2, high=2):
    ctx = TrustContext("ctx-v2", epoch, epoch, epoch, epoch, TemporalHighWater(high, high, high, high))
    roots = (TrustRoot("root", epoch, TrustRootStatus.ACTIVE, activated_epoch=0),)
    artifact = SignedArtifact("artifact", "root", epoch, epoch, epoch, epoch, epoch, epoch + 10)
    return ctx, roots, artifact


def test_06_temporal_high_water_rollback_is_blocked():
    ctx, roots, artifact = _trust(epoch=1, high=2)
    assert evaluate_trust(ctx, roots, artifact).decision is TrustDecision.BLOCK

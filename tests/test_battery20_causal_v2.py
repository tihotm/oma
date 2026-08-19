from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope
from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust

def _scope_policy(): return ScopePolicy(scope_policy_id="scope-v2", allowed_paths=("src",), forbidden_paths=("src/secret",), protected_roles=frozenset({"protected"}), review_roles=frozenset({"review"}))
def test_01_changed_transition_cannot_claim_untouched(): assert evaluate_scope(_scope_policy(), (FileTransition("src/a.py","before","after",touched=False),)).decision is ScopeDecision.BLOCK
def test_02_hidden_touch_restore_is_accepted_when_caller_sets_untouched(): assert evaluate_scope(_scope_policy(), (FileTransition("src/a.py","same","same",roles=frozenset({"protected"}),touched=False),)).decision is ScopeDecision.ALLOW
def test_03_omitted_protected_role_allows_changed_file(): assert evaluate_scope(_scope_policy(), (FileTransition("src/a.py","before","after",roles=frozenset(),touched=True),)).decision is ScopeDecision.ALLOW
def test_04_forbidden_touch_restore_can_be_hidden_as_untouched(): assert evaluate_scope(_scope_policy(), (FileTransition("src/secret/key.txt","same","same",touched=False),)).decision is ScopeDecision.ALLOW
def test_05_path_traversal_is_blocked(): assert evaluate_scope(_scope_policy(), (FileTransition("src/../secret.txt","a","b"),)).decision is ScopeDecision.BLOCK
def _trust(epoch=2, high=2): return (TrustContext("ctx-v2",epoch,epoch,epoch,epoch,TemporalHighWater(high,high,high,high)),(TrustRoot("root",epoch,TrustRootStatus.ACTIVE,activated_epoch=0),),SignedArtifact("artifact","root",epoch,epoch,epoch,epoch,epoch,epoch+10))
def test_06_temporal_high_water_rollback_is_blocked(): c,r,a=_trust(1,2); assert evaluate_trust(c,r,a).decision is TrustDecision.BLOCK
def test_07_lowered_current_and_high_water_are_accepted_without_durable_memory(): c,r,a=_trust(1,1); assert evaluate_trust(c,r,a).decision is TrustDecision.ALLOW
def test_08_future_trust_epoch_is_blocked():
    c,r,a=_trust(2,2); c=TrustContext("ctx-v2",1,2,2,2,TemporalHighWater(1,2,2,2)); assert evaluate_trust(c,r,a).decision is TrustDecision.BLOCK
def test_09_expired_artifact_is_stale():
    root=TrustRoot("root",1,TrustRootStatus.ACTIVE,activated_epoch=0); a=SignedArtifact("a","root",1,1,1,1,1,2); c=TrustContext("ctx",1,1,3,1,TemporalHighWater(1,1,3,1)); assert evaluate_trust(c,(root,),a).decision is TrustDecision.STALE
def test_10_unrelated_cyclic_roots_do_not_block_selected_root():
    roots=(TrustRoot("root",2,TrustRootStatus.ACTIVE,activated_epoch=0),TrustRoot("x",1,TrustRootStatus.ACTIVE,parent_root_id="y",activated_epoch=0),TrustRoot("y",2,TrustRootStatus.ACTIVE,parent_root_id="x",activated_epoch=0)); a=SignedArtifact("a","root",2,2,2,2,2,9); c=TrustContext("ctx",2,2,2,2,TemporalHighWater(2,2,2,2)); assert evaluate_trust(c,roots,a).decision is TrustDecision.ALLOW

import pytest
from oma.trust import *

def root(**o):
    v=dict(root_id="root:2", trust_epoch=2, status=TrustRootStatus.ACTIVE,
           parent_root_id="root:1", activated_epoch=2, retired_epoch=None, compromised_epoch=None)
    v.update(o); return TrustRoot(**v)
def parent(**o):
    v=dict(root_id="root:1", trust_epoch=1, status=TrustRootStatus.RETIRED,
           parent_root_id=None, activated_epoch=1, retired_epoch=2, compromised_epoch=None)
    v.update(o); return TrustRoot(**v)
def high(**o):
    v=dict(trust_epoch=2, authority_epoch=5, logical_epoch=10, state_version=7)
    v.update(o); return TemporalHighWater(**v)
def ctx(**o):
    v=dict(temporal_context_id="time:1", current_trust_epoch=2, current_authority_epoch=5,
           current_logical_epoch=10, current_state_version=7, high_water=high())
    v.update(o); return TrustContext(**v)
def art(**o):
    v=dict(artifact_id="a:1", issuer_root_id="root:2", trust_epoch=2, authority_epoch=5,
           logical_epoch=10, state_version=7, issued_epoch=5, expires_epoch=12)
    v.update(o); return SignedArtifact(**v)

def ev(c=None, roots=None, a=None):
    return evaluate_trust(c or ctx(), roots or [parent(), root()], a or art())

def test_active_current_allows(): assert ev().decision is TrustDecision.ALLOW
def test_retired_historical_is_stale():
    r=parent(status=TrustRootStatus.RETIRED, retired_epoch=2)
    a=art(issuer_root_id="root:1", trust_epoch=1, issued_epoch=1)
    assert evaluate_trust(ctx(), [r], a).decision is TrustDecision.STALE
def test_retired_post_boundary_blocks():
    r=parent(status=TrustRootStatus.RETIRED, retired_epoch=2)
    a=art(issuer_root_id="root:1", trust_epoch=1, issued_epoch=2)
    assert evaluate_trust(ctx(), [r], a).decision is TrustDecision.BLOCK
def test_compromised_historical_blocks_current_admissibility():
    r=parent(status=TrustRootStatus.COMPROMISED, retired_epoch=None, compromised_epoch=2)
    a=art(issuer_root_id="root:1", trust_epoch=1, issued_epoch=1)
    assert evaluate_trust(ctx(), [r], a).decision is TrustDecision.BLOCK
def test_issued_after_compromise_blocks():
    r=parent(status=TrustRootStatus.COMPROMISED, retired_epoch=None, compromised_epoch=2)
    a=art(issuer_root_id="root:1", trust_epoch=1, issued_epoch=2)
    res=evaluate_trust(ctx(), [r], a); assert res.decision is TrustDecision.BLOCK and res.reasons==("issued_after_compromise",)
@pytest.mark.parametrize("field", ["current_trust_epoch","current_authority_epoch","current_logical_epoch","current_state_version"])
def test_high_water_rollback_blocks(field):
    vals={"current_trust_epoch":1,"current_authority_epoch":4,"current_logical_epoch":9,"current_state_version":6}
    assert ev(c=ctx(**{field:vals[field]})).decision is TrustDecision.BLOCK
def test_future_trust_epoch_blocks(): assert ev(a=art(trust_epoch=3)).decision is TrustDecision.BLOCK
def test_future_authority_epoch_blocks(): assert ev(a=art(authority_epoch=6)).decision is TrustDecision.BLOCK
def test_future_logical_epoch_blocks(): assert ev(a=art(logical_epoch=11)).decision is TrustDecision.BLOCK
def test_future_state_version_blocks(): assert ev(a=art(state_version=8)).decision is TrustDecision.BLOCK
def test_old_trust_epoch_is_stale_when_root_active():
    r=TrustRoot("root:1",1,TrustRootStatus.ACTIVE,None,1,None,None)
    a=art(issuer_root_id="root:1", trust_epoch=1, issued_epoch=1)
    assert evaluate_trust(ctx(),[r],a).decision is TrustDecision.STALE
def test_old_authority_epoch_stale(): assert ev(a=art(authority_epoch=4)).decision is TrustDecision.STALE
def test_old_logical_epoch_stale(): assert ev(a=art(logical_epoch=9)).decision is TrustDecision.STALE
def test_old_state_version_stale(): assert ev(a=art(state_version=6)).decision is TrustDecision.STALE
def test_expired_is_stale():
    c=ctx(current_logical_epoch=13, high_water=high(logical_epoch=10))
    assert ev(c=c).decision is TrustDecision.STALE
def test_future_issued_epoch_blocks(): assert ev(a=art(issued_epoch=11,expires_epoch=12)).decision is TrustDecision.BLOCK
def test_unknown_root_blocks(): assert ev(a=art(issuer_root_id="root:x")).decision is TrustDecision.BLOCK
def test_lineage_missing_parent_blocks(): assert evaluate_trust(ctx(),[root(parent_root_id="missing")],art()).decision is TrustDecision.BLOCK
def test_lineage_cycle_blocks():
    r1=TrustRoot("root:1",1,TrustRootStatus.ACTIVE,"root:2",1,None,None)
    r2=TrustRoot("root:2",2,TrustRootStatus.ACTIVE,"root:1",2,None,None)
    assert evaluate_trust(ctx(),[r1,r2],art()).decision is TrustDecision.BLOCK
def test_lineage_epoch_must_increase():
    r1=TrustRoot("root:1",2,TrustRootStatus.ACTIVE,None,1,None,None)
    r2=root(trust_epoch=2,parent_root_id="root:1")
    assert evaluate_trust(ctx(),[r1,r2],art()).decision is TrustDecision.BLOCK
def test_duplicate_root_blocks(): assert evaluate_trust(ctx(),[root(),root()],art()).decision is TrustDecision.BLOCK
def test_missing_retirement_boundary_blocks():
    r=root(status=TrustRootStatus.RETIRED,retired_epoch=None)
    assert evaluate_trust(ctx(),[parent(),r],art()).decision is TrustDecision.BLOCK
def test_missing_compromise_boundary_blocks():
    r=root(status=TrustRootStatus.COMPROMISED,compromised_epoch=None)
    assert evaluate_trust(ctx(),[parent(),r],art()).decision is TrustDecision.BLOCK
def test_temporal_violation_precedes_expiry():
    c=ctx(current_logical_epoch=9, high_water=high(logical_epoch=10))
    a=art(expires_epoch=8)
    res=evaluate_trust(c,[parent(),root()],a)
    assert res.decision is TrustDecision.BLOCK and res.reasons==("temporal_high_water_rollback",)

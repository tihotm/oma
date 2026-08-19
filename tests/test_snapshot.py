from dataclasses import replace

from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def snapshot(**overrides):
    values = dict(
        acceptance_snapshot_id="snapshot-1",
        subject_id="subject-1",
        subject_state_id="state-1",
        policy_bundle_id="policy-1",
        obligation_root="obligation-root-1",
        evidence_root="evidence-root-1",
        ledger_head="ledger-1",
        state_version=7,
        terminal_epoch=3,
        policy_bundle_root="policy-root-1",
    )
    values.update(overrides)
    return AcceptanceSnapshot(**values)


def current(**overrides):
    values = dict(
        subject_id="subject-1",
        subject_state_id="state-1",
        policy_bundle_id="policy-1",
        obligation_root="obligation-root-1",
        evidence_root="evidence-root-1",
        ledger_head="ledger-1",
        state_version=7,
        terminal_epoch=3,
        policy_bundle_root="policy-root-1",
    )
    values.update(overrides)
    return CommitState(**values)


def evaluate(s=None, c=None):
    return evaluate_snapshot_freshness(s or snapshot(), c or current())


def test_exact_match_allows():
    assert evaluate().decision is SnapshotDecision.ALLOW


def test_subject_mismatch_blocks():
    assert evaluate(c=current(subject_id="other")).decision is SnapshotDecision.BLOCK


def test_state_version_rollback_blocks():
    result = evaluate(c=current(state_version=6))
    assert result.decision is SnapshotDecision.BLOCK
    assert result.reasons == ("snapshot_rollback:state_version",)


def test_terminal_epoch_rollback_blocks():
    result = evaluate(c=current(terminal_epoch=2))
    assert result.decision is SnapshotDecision.BLOCK
    assert result.reasons == ("snapshot_rollback:terminal_epoch",)


def test_both_rollbacks_block():
    result = evaluate(c=current(state_version=6, terminal_epoch=2))
    assert result.decision is SnapshotDecision.BLOCK
    assert result.reasons == (
        "snapshot_rollback:state_version",
        "snapshot_rollback:terminal_epoch",
    )


def test_state_version_forward_drift_is_stale():
    assert evaluate(c=current(state_version=8)).decision is SnapshotDecision.STALE


def test_terminal_epoch_forward_drift_is_stale():
    assert evaluate(c=current(terminal_epoch=4)).decision is SnapshotDecision.STALE


def test_subject_state_drift_is_stale():
    assert evaluate(c=current(subject_state_id="state-2")).decision is SnapshotDecision.STALE


def test_policy_bundle_id_drift_is_stale():
    assert evaluate(c=current(policy_bundle_id="policy-2")).decision is SnapshotDecision.STALE


def test_policy_bundle_root_drift_is_stale():
    assert evaluate(c=current(policy_bundle_root="policy-root-2")).decision is SnapshotDecision.STALE


def test_obligation_root_drift_is_stale():
    assert evaluate(c=current(obligation_root="obligation-root-2")).decision is SnapshotDecision.STALE


def test_evidence_root_drift_is_stale():
    assert evaluate(c=current(evidence_root="evidence-root-2")).decision is SnapshotDecision.STALE


def test_ledger_head_drift_is_stale():
    assert evaluate(c=current(ledger_head="ledger-2")).decision is SnapshotDecision.STALE


def test_rollback_precedes_binding_stale():
    result = evaluate(c=current(state_version=6, evidence_root="other"))
    assert result.decision is SnapshotDecision.BLOCK


def test_invalid_snapshot_blocks():
    assert evaluate(s=snapshot(acceptance_snapshot_id="")).decision is SnapshotDecision.BLOCK


def test_negative_snapshot_version_blocks():
    assert evaluate(s=snapshot(state_version=-1)).decision is SnapshotDecision.BLOCK


def test_invalid_current_state_blocks():
    assert evaluate(c=current(ledger_head="")).decision is SnapshotDecision.BLOCK


def test_negative_current_epoch_blocks():
    assert evaluate(c=current(terminal_epoch=-1)).decision is SnapshotDecision.BLOCK


def test_missing_policy_roots_on_both_sides_can_match_for_legacy_slice():
    assert evaluate(
        s=replace(snapshot(), policy_bundle_root=None),
        c=replace(current(), policy_bundle_root=None),
    ).decision is SnapshotDecision.ALLOW

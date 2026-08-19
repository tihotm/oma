from dataclasses import replace

from oma.commit import (
    AcceptanceSnapshot,
    CommitDecision,
    CommitState,
    CommitToken,
    evaluate_commit,
)


def snapshot(**overrides):
    values = dict(
        acceptance_snapshot_id="snap:1",
        subject_id="subject:1",
        subject_state_id="state:1",
        policy_bundle_id="policy:1",
        obligation_root="obligations:1",
        evidence_root="evidence:1",
        ledger_head="ledger:1",
        state_version=7,
        terminal_epoch=2,
    )
    values.update(overrides)
    return AcceptanceSnapshot(**values)


def token(**overrides):
    values = dict(
        token_id="token:1",
        acceptance_snapshot_id="snap:1",
        subject_id="subject:1",
        terminal_epoch=2,
        single_use=True,
    )
    values.update(overrides)
    return CommitToken(**values)


def current(**overrides):
    values = dict(
        subject_id="subject:1",
        subject_state_id="state:1",
        policy_bundle_id="policy:1",
        obligation_root="obligations:1",
        evidence_root="evidence:1",
        ledger_head="ledger:1",
        state_version=7,
        terminal_epoch=2,
        consumed_token_ids=frozenset(),
        terminal_commit_ids=frozenset(),
    )
    values.update(overrides)
    return CommitState(**values)


def test_matching_snapshot_and_token_are_allowed():
    assert evaluate_commit(snapshot(), token(), current(), terminal_commit_id="commit:1").decision is CommitDecision.ALLOW


def test_subject_state_drift_is_stale():
    assert evaluate_commit(snapshot(), token(), current(subject_state_id="state:2"), terminal_commit_id="commit:1").decision is CommitDecision.STALE


def test_policy_bundle_drift_is_stale():
    assert evaluate_commit(snapshot(), token(), current(policy_bundle_id="policy:2"), terminal_commit_id="commit:1").decision is CommitDecision.STALE


def test_obligation_root_drift_is_stale():
    assert evaluate_commit(snapshot(), token(), current(obligation_root="obligations:2"), terminal_commit_id="commit:1").decision is CommitDecision.STALE


def test_evidence_root_drift_is_stale():
    assert evaluate_commit(snapshot(), token(), current(evidence_root="evidence:2"), terminal_commit_id="commit:1").decision is CommitDecision.STALE


def test_ledger_head_drift_is_stale():
    assert evaluate_commit(snapshot(), token(), current(ledger_head="ledger:2"), terminal_commit_id="commit:1").decision is CommitDecision.STALE


def test_state_version_drift_is_stale():
    assert evaluate_commit(snapshot(), token(), current(state_version=8), terminal_commit_id="commit:1").decision is CommitDecision.STALE


def test_terminal_epoch_drift_is_stale():
    assert evaluate_commit(snapshot(), token(), current(terminal_epoch=3), terminal_commit_id="commit:1").decision is CommitDecision.STALE


def test_token_snapshot_mismatch_blocks():
    assert evaluate_commit(snapshot(), token(acceptance_snapshot_id="snap:2"), current(), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_token_subject_mismatch_blocks():
    assert evaluate_commit(snapshot(), token(subject_id="subject:2"), current(), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_token_terminal_epoch_mismatch_blocks():
    assert evaluate_commit(snapshot(), token(terminal_epoch=3), current(), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_current_subject_mismatch_blocks():
    assert evaluate_commit(snapshot(), token(), current(subject_id="subject:2"), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_replayed_token_conflicts():
    state = current(consumed_token_ids=frozenset({"token:1"}))
    result = evaluate_commit(snapshot(), token(), state, terminal_commit_id="commit:2")
    assert result.decision is CommitDecision.CONFLICT
    assert result.reasons == ("commit_token_replay",)


def test_existing_terminal_commit_conflicts():
    state = current(terminal_commit_ids=frozenset({"commit:old"}))
    result = evaluate_commit(snapshot(), token(token_id="token:2"), state, terminal_commit_id="commit:new")
    assert result.decision is CommitDecision.CONFLICT


def test_second_competing_token_conflicts_after_first_commit():
    state = current(
        consumed_token_ids=frozenset({"token:1"}),
        terminal_commit_ids=frozenset({"commit:1"}),
    )
    competing = token(token_id="token:2")
    assert evaluate_commit(snapshot(), competing, state, terminal_commit_id="commit:2").decision is CommitDecision.CONFLICT


def test_non_single_use_token_blocks():
    assert evaluate_commit(snapshot(), token(single_use=False), current(), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_empty_token_id_blocks():
    assert evaluate_commit(snapshot(), token(token_id=""), current(), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_empty_terminal_commit_id_blocks():
    assert evaluate_commit(snapshot(), token(), current(), terminal_commit_id="").decision is CommitDecision.BLOCK


def test_empty_snapshot_id_blocks():
    assert evaluate_commit(snapshot(acceptance_snapshot_id=""), token(), current(), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_negative_state_version_blocks():
    assert evaluate_commit(snapshot(state_version=-1), token(), current(), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_negative_terminal_epoch_blocks():
    assert evaluate_commit(snapshot(terminal_epoch=-1), token(terminal_epoch=-1), current(terminal_epoch=-1), terminal_commit_id="commit:1").decision is CommitDecision.BLOCK


def test_conflict_precedes_stale_for_consumed_token():
    state = current(subject_state_id="state:2", consumed_token_ids=frozenset({"token:1"}))
    assert evaluate_commit(snapshot(), token(), state, terminal_commit_id="commit:2").decision is CommitDecision.CONFLICT


def test_block_precedes_conflict_for_bad_token_binding():
    state = current(consumed_token_ids=frozenset({"token:1"}))
    bad = token(subject_id="subject:2")
    assert evaluate_commit(snapshot(), bad, state, terminal_commit_id="commit:2").decision is CommitDecision.BLOCK

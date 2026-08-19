from oma.commit import (
    AcceptanceSnapshot,
    CommitDecision,
    CommitState,
    CommitToken,
    evaluate_commit,
)


def snapshot(root="policy-root:1"):
    return AcceptanceSnapshot(
        acceptance_snapshot_id="snap:1",
        subject_id="subject:1",
        subject_state_id="state:1",
        policy_bundle_id="policy:1",
        obligation_root="obligations:1",
        evidence_root="evidence:1",
        ledger_head="ledger:1",
        state_version=1,
        terminal_epoch=1,
        policy_bundle_root=root,
    )


def current(root="policy-root:1"):
    return CommitState(
        subject_id="subject:1",
        subject_state_id="state:1",
        policy_bundle_id="policy:1",
        obligation_root="obligations:1",
        evidence_root="evidence:1",
        ledger_head="ledger:1",
        state_version=1,
        terminal_epoch=1,
        policy_bundle_root=root,
    )


def token():
    return CommitToken(
        token_id="token:1",
        acceptance_snapshot_id="snap:1",
        subject_id="subject:1",
        terminal_epoch=1,
    )


def test_matching_policy_bundle_root_allows():
    result = evaluate_commit(snapshot(), token(), current(), terminal_commit_id="commit:1")
    assert result.decision is CommitDecision.ALLOW


def test_policy_bundle_root_drift_is_stale():
    result = evaluate_commit(
        snapshot(),
        token(),
        current("policy-root:2"),
        terminal_commit_id="commit:1",
    )
    assert result.decision is CommitDecision.STALE
    assert result.reasons == ("snapshot_drift:policy_bundle_root",)

from oma.execution import _atomic_observation
from oma.validation import ValidationDecision


def test_v11_19_atomic_proof_length_prefix_separates_reason_boundaries():
    left = _atomic_observation(
        ValidationDecision.BLOCK,
        acceptance_snapshot_id="snapshot:1",
        token_id="token:1",
        terminal_commit_id="commit:1",
        reasons=("a", "bc"),
    )
    right = _atomic_observation(
        ValidationDecision.BLOCK,
        acceptance_snapshot_id="snapshot:1",
        token_id="token:1",
        terminal_commit_id="commit:1",
        reasons=("ab", "c"),
    )
    assert left.evidence_root != right.evidence_root

from oma.execution import _atomic_observation
from oma.validation import ValidationDecision


def test_v11_20_atomic_proof_length_prefix_separates_identifier_boundaries():
    left = _atomic_observation(
        ValidationDecision.ACCEPT,
        acceptance_snapshot_id="a:b",
        token_id="c",
        terminal_commit_id="d",
    )
    right = _atomic_observation(
        ValidationDecision.ACCEPT,
        acceptance_snapshot_id="a",
        token_id="b:c",
        terminal_commit_id="d",
    )
    assert left.evidence_root != right.evidence_root

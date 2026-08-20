from oma.execution import _atomic_observation
from oma.validation import ValidationDecision


def test_v11_18_atomic_proof_currently_accepts_empty_terminal_commit_id():
    observation = _atomic_observation(
        ValidationDecision.ACCEPT,
        acceptance_snapshot_id="snapshot:1",
        token_id="token:1",
        terminal_commit_id="",
    )
    assert observation.evidence_root

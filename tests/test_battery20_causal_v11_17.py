from oma.execution import _atomic_observation
from oma.validation import ValidationDecision


def test_v11_17_atomic_proof_currently_accepts_empty_token_id():
    observation = _atomic_observation(
        ValidationDecision.ACCEPT,
        acceptance_snapshot_id="snapshot:1",
        token_id="",
        terminal_commit_id="commit:1",
    )
    assert observation.evidence_root

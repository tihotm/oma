from oma.execution import _atomic_observation
from oma.validation import ValidationDecision


def test_v11_16_atomic_proof_currently_accepts_empty_snapshot_id():
    observation = _atomic_observation(
        ValidationDecision.ACCEPT,
        acceptance_snapshot_id="",
        token_id="token:1",
        terminal_commit_id="commit:1",
    )
    assert observation.evidence_root

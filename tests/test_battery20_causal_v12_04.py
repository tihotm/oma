import pytest

from oma.policy import policy_object_root


def test_v12_04_non_bool_evidence_passed_is_rejected():
    value = {
        "evidence_id": "ev:1",
        "obligation_id": "ob:1",
        "subject_id": "subject:1",
        "subject_state_id": "state:1",
        "verification_context_id": "verify:1",
        "policy_bundle_id": "bundle:1",
        "passed": "true",
    }
    with pytest.raises(ValueError):
        policy_object_root("evidence-payload", value)

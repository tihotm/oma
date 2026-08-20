from oma.policy import policy_object_root


def payload(passed):
    return {
        "evidence_id": "ev:1",
        "obligation_id": "ob:1",
        "subject_id": "subject:1",
        "subject_state_id": "state:1",
        "verification_context_id": "verify:1",
        "policy_bundle_id": "bundle:1",
        "passed": passed,
    }


def test_v12_03_evidence_payload_passed_bit_changes_root():
    assert policy_object_root("evidence-payload", payload(True)) != policy_object_root("evidence-payload", payload(False))

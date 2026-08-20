from oma.policy import policy_object_root


def test_v12_02_evidence_payload_control_identifier_currently_hashes():
    value = {
        "evidence_id": "ev\0shadow",
        "obligation_id": "ob:1",
        "subject_id": "subject:1",
        "subject_state_id": "state:1",
        "verification_context_id": "verify:1",
        "policy_bundle_id": "bundle:1",
        "passed": True,
    }
    assert policy_object_root("evidence-payload", value)

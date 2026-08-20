from oma.policy import policy_object_root


def payload(subject_id):
    return {
        "evidence_id": "ev:1",
        "obligation_id": "ob:1",
        "subject_id": subject_id,
        "subject_state_id": "state:1",
        "verification_context_id": "verify:1",
        "policy_bundle_id": "bundle:1",
        "passed": True,
    }


def test_v12_05_evidence_subject_binding_changes_root_without_controls():
    assert policy_object_root("evidence-payload", payload("subject:1")) != policy_object_root("evidence-payload", payload("subject:2"))

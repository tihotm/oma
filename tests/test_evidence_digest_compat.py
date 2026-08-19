import hashlib

from oma.policy import policy_object_root


def test_evidence_payload_root_preserves_oma_evidence_v1_domain():
    value = {
        "evidence_id": "evidence-1",
        "obligation_id": "obligation-1",
        "subject_id": "subject-1",
        "subject_state_id": "state-1",
        "verification_context_id": "verify-1",
        "policy_bundle_id": "policy-1",
        "passed": True,
    }
    payload = "\0".join(
        (
            "evidence-1",
            "obligation-1",
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            "1",
        )
    ).encode("utf-8")
    expected = hashlib.sha256(b"oma:evidence:v1\0" + payload).hexdigest()
    assert policy_object_root("evidence-payload", value) == expected


def test_evidence_payload_root_changes_when_passed_changes():
    base = {
        "evidence_id": "evidence-1",
        "obligation_id": "obligation-1",
        "subject_id": "subject-1",
        "subject_state_id": "state-1",
        "verification_context_id": "verify-1",
        "policy_bundle_id": "policy-1",
        "passed": True,
    }
    failed = {**base, "passed": False}
    assert policy_object_root("evidence-payload", base) != policy_object_root(
        "evidence-payload",
        failed,
    )

from oma.policy import policy_object_root


def payload(**overrides):
    value = dict(
        evidence_id="a",
        obligation_id="b",
        subject_id="subject:1",
        subject_state_id="state:1",
        verification_context_id="verify:1",
        policy_bundle_id="bundle:1",
        passed=True,
    )
    value.update(overrides)
    return value


def test_v12_01_evidence_payload_root_delimiter_collision_is_reachable():
    left = payload(evidence_id="a", obligation_id="b\0c")
    right = payload(evidence_id="a\0b", obligation_id="c")
    assert left != right
    assert policy_object_root("evidence-payload", left) == policy_object_root("evidence-payload", right)

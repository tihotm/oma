from oma.policy import policy_object_root


def test_policy_root_finite_payload_is_deterministic():
    left = policy_object_root("probe", {"value": 7, "label": "ok"})
    right = policy_object_root("probe", {"label": "ok", "value": 7})
    assert left == right

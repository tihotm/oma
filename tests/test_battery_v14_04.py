from oma.policy import policy_object_root


def test_policy_root_currently_accepts_unsafe_json_integer():
    root = policy_object_root("probe", {"value": 2**60})
    assert isinstance(root, str) and len(root) == 64

from oma.policy import policy_object_root


def test_policy_root_currently_accepts_nan():
    root = policy_object_root("probe", {"value": float("nan")})
    assert isinstance(root, str) and len(root) == 64

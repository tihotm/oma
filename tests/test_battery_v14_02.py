from oma.policy import policy_object_root


def test_policy_root_currently_accepts_infinity():
    root = policy_object_root("probe", {"value": float("inf")})
    assert isinstance(root, str) and len(root) == 64

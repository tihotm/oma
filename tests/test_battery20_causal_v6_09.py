from oma.policy import policy_object_root


def test_09_set_order_is_deterministic():
    assert policy_object_root("probe", {"a", "b", "c"}) == policy_object_root("probe", frozenset({"c", "b", "a"}))

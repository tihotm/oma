from oma.policy import policy_object_root


def test_08_distinct_keys_can_collapse_and_overwrite():
    assert policy_object_root("probe", {1: "a", "1": "b"}) == policy_object_root("probe", {"1": "b"})

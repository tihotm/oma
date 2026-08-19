from oma.policy import policy_object_root


def test_06_none_and_string_none_keys_collide():
    assert policy_object_root("probe", {None: "x"}) == policy_object_root("probe", {"None": "x"})

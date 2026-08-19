from oma.policy import policy_object_root


def test_07_boolean_and_string_boolean_keys_collide():
    assert policy_object_root("probe", {True: "x"}) == policy_object_root("probe", {"True": "x"})

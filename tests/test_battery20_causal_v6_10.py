from oma.policy import policy_object_root


def test_10_tuple_and_list_values_collide():
    assert policy_object_root("probe", ("a", "b")) == policy_object_root("probe", ["a", "b"])

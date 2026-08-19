from oma.policy import policy_object_root


def test_15_policy_object_key_coercion_collision_observed():
    ambiguous = {1: "left", "1": "right"}
    collapsed = {"1": "right"}
    assert policy_object_root("probe", ambiguous) == policy_object_root("probe", collapsed)

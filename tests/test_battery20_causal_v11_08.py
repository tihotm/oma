from oma.policy import PolicyBinding, PolicyBundle, policy_bundle_root


def test_v11_08_policy_bundle_root_delimiter_collision_is_observed():
    left = PolicyBundle(
        "bundle:1",
        1,
        (PolicyBinding("a", "i", "r\nb\0j\0s"),),
    )
    right = PolicyBundle(
        "bundle:1",
        1,
        (
            PolicyBinding("a", "i", "r"),
            PolicyBinding("b", "j", "s"),
        ),
    )
    assert left != right
    assert policy_bundle_root(left) == policy_bundle_root(right)

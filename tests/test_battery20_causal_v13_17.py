from oma.aggregation import AggregationPolicy
from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle, policy_object_root


def test_v13_17_policy_bundle_accepts_type_erased_aggregation_binding():
    left = AggregationPolicy("agg:v1", "set:1", frozenset({"ev:1"}), "subject:1", "state:1", "verify:1", "bundle:1", "pair:1", "run:1")
    right = AggregationPolicy("agg:v1", "set:1", ["ev:1"], "subject:1", "state:1", "verify:1", "bundle:1", "pair:1", "run:1")
    expected = PolicyBundle("bundle:1", 1, (PolicyBinding("aggregation", "agg:v1", policy_object_root("aggregation", left)),))
    presented = PolicyBundle("bundle:1", 1, (PolicyBinding("aggregation", "agg:v1", policy_object_root("aggregation", right)),))
    assert left != right
    assert evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"aggregation"})).decision is PolicyBundleDecision.ALLOW

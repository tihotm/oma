from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation


def evaluate(subject_id, subject_state_id):
    policy = AggregationPolicy(
        "agg:v1",
        "set:1",
        frozenset({"ev:1"}),
        subject_id,
        subject_state_id,
        "verify:1",
        "bundle:1",
        "pair:1",
        "run:1",
    )
    item = AggregationItem(
        "ev:1",
        "digest:1",
        subject_id,
        subject_state_id,
        "verify:1",
        "bundle:1",
        "pair:1",
        "run:1",
        True,
    )
    return evaluate_aggregation(policy, (item,))


def test_v12_18_valid_aggregation_inputs_can_collide_across_subject_state_boundary():
    left = evaluate("a", "b\0c")
    right = evaluate("a\0b", "c")
    assert left.decision is AggregationDecision.ALLOW
    assert right.decision is AggregationDecision.ALLOW
    assert left.aggregation_root == right.aggregation_root

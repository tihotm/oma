from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation


def test_08_cross_run_aggregation_evidence_blocks():
    policy = AggregationPolicy("agg", "set", frozenset({"e1"}), "s", "st", "ctx", "bundle", "pair", "run-a")
    item = AggregationItem("e1", "d", "s", "st", "ctx", "bundle", "pair", "run-b", True)
    result = evaluate_aggregation(policy, (item,))
    assert result.decision is AggregationDecision.BLOCK
    assert "aggregation_run_mismatch:e1" in result.reasons

from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation


def test_07_unexpected_aggregation_evidence_blocks():
    policy = AggregationPolicy("agg", "set", frozenset({"e1"}), "s", "st", "ctx", "bundle", "pair", "run")
    item = AggregationItem("e2", "d", "s", "st", "ctx", "bundle", "pair", "run", True)
    result = evaluate_aggregation(policy, (item,))
    assert result.decision is AggregationDecision.BLOCK
    assert "unexpected_aggregation_evidence:e2" in result.reasons

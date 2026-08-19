from oma.aggregation import AggregationDecision, AggregationPolicy, evaluate_aggregation


def test_06_missing_expected_aggregation_evidence_is_not_done():
    policy = AggregationPolicy("agg", "set", frozenset({"e1"}), "s", "st", "ctx", "bundle", "pair", "run")
    result = evaluate_aggregation(policy, ())
    assert result.decision is AggregationDecision.NOT_DONE
    assert "missing_expected_evidence:e1" in result.reasons

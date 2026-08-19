from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation


def test_run_mismatch_is_blocked():
    p=AggregationPolicy("agg","set",frozenset({"e"}),"s","st","v","pb","pair","run")
    i=AggregationItem("e","d","s","st","v","pb","pair","other",True)
    assert evaluate_aggregation(p,(i,)).decision is AggregationDecision.BLOCK

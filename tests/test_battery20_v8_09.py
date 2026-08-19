from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation


def test_unexpected_evidence_is_blocked():
    p=AggregationPolicy("agg","set",frozenset({"e"}),"s","st","v","pb","pair","run")
    e=AggregationItem("e","d","s","st","v","pb","pair","run",True)
    x=AggregationItem("x","dx","s","st","v","pb","pair","run",True)
    assert evaluate_aggregation(p,(e,x)).decision is AggregationDecision.BLOCK

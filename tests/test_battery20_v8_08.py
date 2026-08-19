from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation


def test_integer_one_is_accepted_as_passed_evidence():
    p=AggregationPolicy("agg","set",frozenset({"e"}),"s","st","v","pb","pair","run")
    i=AggregationItem("e","d","s","st","v","pb","pair","run",1)
    assert evaluate_aggregation(p,(i,)).decision is AggregationDecision.ALLOW

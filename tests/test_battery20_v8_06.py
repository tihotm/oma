from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation


def test_distinct_bound_contexts_can_share_aggregation_root_via_nul_shift():
    p1=AggregationPolicy("agg","set",frozenset({"e"}),"s","x\x00y","v","pb","pair","run")
    p2=AggregationPolicy("agg","set",frozenset({"e"}),"s\x00x","y","v","pb","pair","run")
    i1=AggregationItem("e","d","s","x\x00y","v","pb","pair","run",True)
    i2=AggregationItem("e","d","s\x00x","y","v","pb","pair","run",True)
    r1=evaluate_aggregation(p1,(i1,)); r2=evaluate_aggregation(p2,(i2,))
    assert r1.decision is AggregationDecision.ALLOW and r2.decision is AggregationDecision.ALLOW
    assert r1.aggregation_root == r2.aggregation_root

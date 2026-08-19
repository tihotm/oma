from oma.aggregation import AggregationPolicy, aggregation_root


def test_distinct_expected_evidence_sets_can_share_empty_item_root():
    a=AggregationPolicy("agg","set",frozenset({"a","b"}),"s","st","v","pb","pair","run")
    b=AggregationPolicy("agg","set",frozenset({"a,b"}),"s","st","v","pb","pair","run")
    assert a != b
    assert aggregation_root(a,()) == aggregation_root(b,())

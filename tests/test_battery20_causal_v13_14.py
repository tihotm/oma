import pytest

from oma.aggregation import AggregationDecision, AggregationItem, AggregationPolicy, evaluate_aggregation
from oma.policy import policy_object_root


def test_v13_14_root_equivalent_aggregation_container_type_can_crash_gate():
    left = AggregationPolicy("agg:v1", "set:1", frozenset({"ev:1"}), "subject:1", "state:1", "verify:1", "bundle:1", "pair:1", "run:1")
    right = AggregationPolicy("agg:v1", "set:1", ["ev:1"], "subject:1", "state:1", "verify:1", "bundle:1", "pair:1", "run:1")
    item = AggregationItem("ev:1", "digest:1", "subject:1", "state:1", "verify:1", "bundle:1", "pair:1", "run:1", True)
    assert policy_object_root("aggregation", left) == policy_object_root("aggregation", right)
    assert evaluate_aggregation(left, (item,)).decision is AggregationDecision.ALLOW
    with pytest.raises(TypeError):
        evaluate_aggregation(right, (item,))

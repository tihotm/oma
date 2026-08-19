from dataclasses import replace
from oma.validation import ValidationDecision
from oma.pipeline import evaluate_composed_pipeline
from test_pipeline import valid_input


def test_pipeline_blocks_empty_acceptance_denominator():
    item = valid_input()
    attack = replace(item, acceptance_context=replace(item.acceptance_context, required_obligations=frozenset()), evidence=())
    assert evaluate_composed_pipeline(attack).result.decision is ValidationDecision.BLOCK

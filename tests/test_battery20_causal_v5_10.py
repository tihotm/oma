from dataclasses import replace
from oma.validation import ValidationDecision
from oma.pipeline import evaluate_composed_pipeline
from test_pipeline import valid_input


def test_pipeline_blocks_empty_obligation_identity():
    item = valid_input()
    context = replace(item.acceptance_context, required_obligations=frozenset({""}))
    evidence = replace(item.evidence[0], obligation_id="")
    attack = replace(item, acceptance_context=context, evidence=(evidence,))
    assert evaluate_composed_pipeline(attack).result.decision is ValidationDecision.BLOCK

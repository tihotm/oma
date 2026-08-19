from dataclasses import replace
from oma.validation import ValidationDecision
from oma.pipeline import evaluate_composed_pipeline
from test_pipeline import valid_input


def test_pipeline_blocks_empty_acceptance_bindings():
    item = valid_input()
    context = replace(item.acceptance_context, subject_id="", subject_state_id="", verification_context_id="", policy_bundle_id="")
    evidence = replace(item.evidence[0], subject_id="", subject_state_id="", verification_context_id="", policy_bundle_id="")
    attack = replace(item, acceptance_context=context, evidence=(evidence,))
    assert evaluate_composed_pipeline(attack).result.decision is ValidationDecision.BLOCK

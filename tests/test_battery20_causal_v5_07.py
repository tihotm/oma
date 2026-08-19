from dataclasses import replace
from oma.validation import ValidationDecision
from oma.pipeline import evaluate_composed_pipeline
from test_pipeline import valid_input


def test_pipeline_blocks_empty_evidence_id_via_provenance_binding():
    item = valid_input()
    attack = replace(item, evidence=(replace(item.evidence[0], evidence_id=""),))
    assert evaluate_composed_pipeline(attack).result.decision is ValidationDecision.BLOCK

from dataclasses import replace
import pytest
from oma.pipeline import evaluate_composed_pipeline
from test_pipeline import valid_input


def test_non_boolean_evidence_pass_flag_currently_raises_in_pipeline():
    item = valid_input()
    attack = replace(item, evidence=(replace(item.evidence[0], passed=1),))
    with pytest.raises(ValueError, match="invalid evidence payload"):
        evaluate_composed_pipeline(attack)

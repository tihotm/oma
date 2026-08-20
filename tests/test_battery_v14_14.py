from dataclasses import replace
from pathlib import Path
import runpy
import pytest

from oma.pipeline import evaluate_composed_pipeline

_pipeline = runpy.run_path(str(Path(__file__).with_name('test_pipeline.py')))
valid_input = _pipeline['valid_input']


def test_pipeline_invalid_identity_policy_currently_raises_attribute_error():
    with pytest.raises(AttributeError):
        evaluate_composed_pipeline(replace(valid_input(), identity_policy=object()))

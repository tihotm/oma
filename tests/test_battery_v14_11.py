from dataclasses import replace
from pathlib import Path
import runpy
import pytest

from oma.identity import StrictSchema
from oma.pipeline import evaluate_composed_pipeline

_pipeline = runpy.run_path(str(Path(__file__).with_name('test_pipeline.py')))
valid_input = _pipeline['valid_input']


def test_pipeline_lone_surrogate_payload_currently_raises():
    item = valid_input()
    item = replace(item, raw_json='{"x":"\\ud800"}', schema=StrictSchema('schema:v1',1,frozenset(),frozenset({'x'})))
    with pytest.raises(UnicodeEncodeError):
        evaluate_composed_pipeline(item)

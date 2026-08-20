from dataclasses import replace
from pathlib import Path
import runpy
import pytest

from oma.identity import StrictSchema
from oma.pipeline import evaluate_composed_pipeline

_pipeline = runpy.run_path(str(Path(__file__).with_name('test_pipeline.py')))
valid_input = _pipeline['valid_input']


def test_pipeline_excessive_json_depth_currently_raises_recursion_error():
    item = valid_input()
    raw = '{"x":' + ('[' * 1500) + '0' + (']' * 1500) + '}'
    item = replace(item, raw_json=raw, schema=StrictSchema('schema:v1',1,frozenset(),frozenset({'x'})))
    with pytest.raises(RecursionError):
        evaluate_composed_pipeline(item)

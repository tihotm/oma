from dataclasses import replace
from pathlib import Path
import runpy

from oma.pipeline import evaluate_composed_pipeline
from oma.validation import ValidationDecision

_pipeline = runpy.run_path(str(Path(__file__).with_name('test_pipeline.py')))
valid_input = _pipeline['valid_input']


def test_pipeline_ordinary_parse_failure_blocks_without_exception():
    result = evaluate_composed_pipeline(replace(valid_input(), raw_json='{} trailing'))
    assert result.result.decision is ValidationDecision.BLOCK

from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.trust import TemporalHighWater
from oma.trust_registry import SQLiteTrustArtifactRegistry, TrustRegistryDecision
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]


def test_newer_registered_trust_epoch_prevents_old_context_terminalization(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    store = initialized_store(path, item)

    newer_context = replace(
        item.trust_context,
        current_trust_epoch=2,
        current_logical_epoch=2,
        high_water=TemporalHighWater(2, 1, 2, 1),
    )
    newer_roots = (replace(item.trust_roots[0], trust_epoch=2, activated_epoch=2),)
    newer_artifact = replace(
        item.signed_artifact,
        artifact_id="artifact-2",
        trust_epoch=2,
        logical_epoch=2,
        issued_epoch=2,
    )
    registered = SQLiteTrustArtifactRegistry(path).register(
        newer_context, newer_roots, newer_artifact
    )
    assert registered.decision is TrustRegistryDecision.WRITTEN

    result = execute_composed_pipeline(item, store)
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0

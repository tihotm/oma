from __future__ import annotations

import hashlib

from .pipeline import ComposedPipelineInput, ComposedPipelineResult, evaluate_composed_pipeline
from .sqlite_commit import DurableCommitDecision, SQLiteTerminalStore
from .validation import (
    ValidationDecision,
    ValidationObservation,
    canonical_validation_graph,
    evaluate_validation_graph,
)


def _atomic_observation(
    decision: ValidationDecision,
    reasons: tuple[str, ...] = (),
) -> ValidationObservation:
    payload = "\0".join(("atomic_commit", decision.value, *reasons)).encode("utf-8")
    root = hashlib.sha256(b"oma:pipeline:v1\0" + payload).hexdigest()
    return ValidationObservation("atomic_commit", decision, root)


def execute_composed_pipeline(
    pipeline_input: ComposedPipelineInput,
    terminal_store: SQLiteTerminalStore,
) -> ComposedPipelineResult:
    """Evaluate every gate, then durably commit only after full prerequisite closure.

    The pure evaluator intentionally leaves ``atomic_commit`` as NOT_DONE. This
    execution boundary replaces only that final observation, and only when all
    prior observations are ACCEPT. The durable store independently re-evaluates
    the same composed input so direct storage usage cannot bypass the closure.
    """
    evaluated = evaluate_composed_pipeline(pipeline_input)
    prior = tuple(item for item in evaluated.observations if item.node_id != "atomic_commit")
    if any(item.decision is not ValidationDecision.ACCEPT for item in prior):
        return evaluated

    durable = terminal_store.commit(pipeline_input)
    mapped = {
        DurableCommitDecision.COMMITTED: ValidationDecision.ACCEPT,
        DurableCommitDecision.STALE: ValidationDecision.STALE,
        DurableCommitDecision.CONFLICT: ValidationDecision.BLOCK,
        DurableCommitDecision.BLOCK: ValidationDecision.BLOCK,
    }[durable.decision]
    observations = prior + (_atomic_observation(mapped, durable.reasons),)
    result = evaluate_validation_graph(canonical_validation_graph(), observations)
    return ComposedPipelineResult(result=result, observations=observations)

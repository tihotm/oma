from __future__ import annotations

from dataclasses import replace
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
    """Evaluate against authoritative state, then commit through the durable CAS.

    The caller-supplied ``commit_state`` is not used as the final source of
    truth when the store has an authoritative subject state. The store repeats
    the same lookup and evaluation inside ``BEGIN IMMEDIATE`` to close the
    read/commit race.
    """
    authoritative = terminal_store.get_subject_state(pipeline_input.snapshot.subject_id)
    effective_input = (
        pipeline_input
        if authoritative is None
        else replace(pipeline_input, commit_state=authoritative)
    )

    evaluated = evaluate_composed_pipeline(effective_input)
    prior = tuple(item for item in evaluated.observations if item.node_id != "atomic_commit")
    if any(item.decision is not ValidationDecision.ACCEPT for item in prior):
        return evaluated

    durable = terminal_store.commit(effective_input)
    mapped = {
        DurableCommitDecision.COMMITTED: ValidationDecision.ACCEPT,
        DurableCommitDecision.STALE: ValidationDecision.STALE,
        DurableCommitDecision.CONFLICT: ValidationDecision.BLOCK,
        DurableCommitDecision.BLOCK: ValidationDecision.BLOCK,
    }[durable.decision]
    observations = prior + (_atomic_observation(mapped, durable.reasons),)
    result = evaluate_validation_graph(canonical_validation_graph(), observations)
    return ComposedPipelineResult(result=result, observations=observations)

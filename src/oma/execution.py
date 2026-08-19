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


def _length_prefixed(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return str(len(encoded)).encode("ascii") + b":" + encoded


def _atomic_observation(
    decision: ValidationDecision,
    *,
    acceptance_snapshot_id: str,
    token_id: str,
    terminal_commit_id: str,
    reasons: tuple[str, ...] = (),
) -> ValidationObservation:
    payload = b"".join(
        _length_prefixed(value)
        for value in (
            "oma:atomic-commit:v1",
            decision.value,
            acceptance_snapshot_id,
            token_id,
            terminal_commit_id,
            *reasons,
        )
    )
    root = hashlib.sha256(payload).hexdigest()
    return ValidationObservation("atomic_commit", decision, root)


def execute_composed_pipeline(
    pipeline_input: ComposedPipelineInput,
    terminal_store: SQLiteTerminalStore,
) -> ComposedPipelineResult:
    """Evaluate against authoritative durable state/history, then commit.

    Caller-supplied ``commit_state`` and ``retry_events`` are not final sources
    of truth when authoritative rows exist. The store repeats both lookups and
    re-evaluates the closure inside ``BEGIN IMMEDIATE`` to close the final race.
    """
    authoritative_state = terminal_store.get_subject_state(
        pipeline_input.snapshot.subject_id
    )
    authoritative_retry_events = terminal_store.get_retry_events(
        pipeline_input.retry_policy,
        pipeline_input.retry_domain,
    )

    replacements = {}
    if authoritative_state is not None:
        replacements["commit_state"] = authoritative_state
    if authoritative_retry_events is not None:
        replacements["retry_events"] = authoritative_retry_events
    effective_input = (
        pipeline_input if not replacements else replace(pipeline_input, **replacements)
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
    observations = prior + (
        _atomic_observation(
            mapped,
            acceptance_snapshot_id=effective_input.snapshot.acceptance_snapshot_id,
            token_id=effective_input.commit_token.token_id,
            terminal_commit_id=(durable.terminal_commit_id or effective_input.terminal_commit_id),
            reasons=durable.reasons,
        ),
    )
    result = evaluate_validation_graph(canonical_validation_graph(), observations)
    return ComposedPipelineResult(result=result, observations=observations)

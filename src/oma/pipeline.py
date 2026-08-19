from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .acceptance import AcceptanceDecision, evaluate_acceptance
from .authority import AuthorityDecision, evaluate_authority
from .commit import CommitDecision, evaluate_commit
from .identity import IdentityDecision, make_typed_identity, strict_parse_json
from .retry import RetryDecision, evaluate_retry_domain
from .scope import ScopeDecision, evaluate_scope
from .trust import TrustDecision, evaluate_trust
from .validation import (
    ValidationDecision,
    ValidationObservation,
    ValidationResult,
    canonical_validation_graph,
    evaluate_validation_graph,
)


@dataclass(frozen=True, slots=True)
class ComposedPipelineInput:
    raw_json: str
    schema: Any
    namespace: str
    raw_id: str
    identity_policy: Any
    scope_policy: Any
    transitions: tuple[Any, ...]
    authority_context: Any
    capabilities: tuple[Any, ...]
    authority_request: Any
    trust_context: Any
    trust_roots: tuple[Any, ...]
    signed_artifact: Any
    acceptance_context: Any
    evidence: tuple[Any, ...]
    retry_policy: Any
    retry_domain: Any
    retry_events: tuple[Any, ...]
    snapshot: Any
    commit_token: Any
    commit_state: Any
    terminal_commit_id: str


@dataclass(frozen=True, slots=True)
class ComposedPipelineResult:
    result: ValidationResult
    observations: tuple[ValidationObservation, ...]


def _evidence_root(
    node_id: str,
    decision: ValidationDecision,
    reasons: tuple[str, ...] = (),
) -> str:
    payload = "\0".join((node_id, decision.value, *reasons)).encode("utf-8")
    return hashlib.sha256(b"oma:pipeline:v1\0" + payload).hexdigest()


def _observation(
    node_id: str,
    decision: ValidationDecision,
    reasons: tuple[str, ...] = (),
) -> ValidationObservation:
    return ValidationObservation(
        node_id=node_id,
        decision=decision,
        evidence_root=_evidence_root(node_id, decision, reasons),
    )


def evaluate_composed_pipeline(
    pipeline_input: ComposedPipelineInput,
) -> ComposedPipelineResult:
    """Evaluate the canonical pipeline using real gate outputs.

    Callers provide domain inputs, not precomputed validation decisions.
    Acceptance-critical stages without a production implementation remain
    NOT_DONE so the composed pipeline cannot manufacture global ACCEPT.
    """
    observations: list[ValidationObservation] = []

    parsed = strict_parse_json(pipeline_input.raw_json, pipeline_input.schema)
    observations.append(
        _observation(
            "parse_schema",
            ValidationDecision.ACCEPT
            if parsed.decision is IdentityDecision.ALLOW
            else ValidationDecision.BLOCK,
            parsed.reasons,
        )
    )

    identity = make_typed_identity(
        pipeline_input.namespace,
        pipeline_input.raw_id,
        pipeline_input.identity_policy,
    )
    observations.append(
        _observation(
            "identity_namespace",
            ValidationDecision.ACCEPT
            if identity.decision is IdentityDecision.ALLOW
            else ValidationDecision.BLOCK,
            identity.reasons,
        )
    )

    scope = evaluate_scope(pipeline_input.scope_policy, pipeline_input.transitions)
    scope_decision = {
        ScopeDecision.ALLOW: ValidationDecision.ACCEPT,
        ScopeDecision.REVIEW: ValidationDecision.NOT_DONE,
        ScopeDecision.BLOCK: ValidationDecision.BLOCK,
    }[scope.decision]
    observations.append(
        _observation("scope_integrity", scope_decision, scope.reasons)
    )

    authority = evaluate_authority(
        pipeline_input.authority_context,
        pipeline_input.capabilities,
        pipeline_input.authority_request,
    )
    authority_decision = {
        AuthorityDecision.ALLOW: ValidationDecision.ACCEPT,
        AuthorityDecision.STALE: ValidationDecision.STALE,
        AuthorityDecision.BLOCK: ValidationDecision.BLOCK,
    }[authority.decision]
    observations.append(
        _observation("authority_capability", authority_decision, authority.reasons)
    )

    trust = evaluate_trust(
        pipeline_input.trust_context,
        pipeline_input.trust_roots,
        pipeline_input.signed_artifact,
    )
    trust_decision = {
        TrustDecision.ALLOW: ValidationDecision.ACCEPT,
        TrustDecision.STALE: ValidationDecision.STALE,
        TrustDecision.BLOCK: ValidationDecision.BLOCK,
    }[trust.decision]
    observations.append(
        _observation("trust_temporal", trust_decision, trust.reasons)
    )

    observations.append(
        _observation(
            "policy_bundle",
            ValidationDecision.NOT_DONE,
            ("policy_bundle_not_implemented",),
        )
    )
    observations.append(
        _observation(
            "snapshot_freshness",
            ValidationDecision.NOT_DONE,
            ("snapshot_freshness_not_implemented",),
        )
    )
    observations.append(
        _observation(
            "provenance",
            ValidationDecision.NOT_DONE,
            ("provenance_not_implemented",),
        )
    )

    acceptance = evaluate_acceptance(
        pipeline_input.acceptance_context,
        pipeline_input.evidence,
    )
    acceptance_decision = {
        AcceptanceDecision.ACCEPT: ValidationDecision.ACCEPT,
        AcceptanceDecision.NOT_DONE: ValidationDecision.NOT_DONE,
        AcceptanceDecision.BLOCK: ValidationDecision.BLOCK,
    }[acceptance.decision]
    observations.append(
        _observation(
            "evidence_qualification",
            acceptance_decision,
            acceptance.reasons,
        )
    )

    observations.append(
        _observation(
            "aggregation",
            ValidationDecision.NOT_DONE,
            ("aggregation_not_implemented",),
        )
    )

    retry = evaluate_retry_domain(
        pipeline_input.retry_policy,
        pipeline_input.retry_domain,
        pipeline_input.retry_events,
    )
    observations.append(
        _observation(
            "retry_recovery",
            ValidationDecision.ACCEPT
            if retry.decision is RetryDecision.ALLOW
            else ValidationDecision.BLOCK,
            retry.reasons,
        )
    )

    observations.append(
        _observation(
            "terminal_barrier",
            ValidationDecision.NOT_DONE,
            ("terminal_barrier_not_implemented",),
        )
    )

    commit = evaluate_commit(
        pipeline_input.snapshot,
        pipeline_input.commit_token,
        pipeline_input.commit_state,
        terminal_commit_id=pipeline_input.terminal_commit_id,
    )
    commit_decision = {
        CommitDecision.ALLOW: ValidationDecision.ACCEPT,
        CommitDecision.STALE: ValidationDecision.STALE,
        CommitDecision.CONFLICT: ValidationDecision.BLOCK,
        CommitDecision.BLOCK: ValidationDecision.BLOCK,
    }[commit.decision]
    observations.append(
        _observation("commit_authorization", commit_decision, commit.reasons)
    )

    observations.append(
        _observation(
            "atomic_commit",
            ValidationDecision.NOT_DONE,
            ("atomic_commit_not_implemented",),
        )
    )

    result = evaluate_validation_graph(
        canonical_validation_graph(),
        observations,
    )
    return ComposedPipelineResult(result=result, observations=tuple(observations))

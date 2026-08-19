from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .acceptance import AcceptanceDecision, evaluate_acceptance
from .authority import AuthorityDecision, evaluate_authority
from .commit import CommitDecision, evaluate_commit
from .identity import IdentityDecision, make_typed_identity, strict_parse_json
from .obligation import ObligationDecision, evaluate_obligation_manifest
from .provenance import ProvenanceDecision, evaluate_provenance
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
    expected_obligation_manifest: Any | None = None
    presented_obligation_manifest: Any | None = None
    provenance_policy: Any | None = None
    provenance_nodes: tuple[Any, ...] | None = None


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


def _evidence_payload_digest(item: Any) -> str:
    payload = "\0".join(
        (
            item.evidence_id,
            item.obligation_id,
            item.subject_id,
            item.subject_state_id,
            item.verification_context_id,
            item.policy_bundle_id,
            "1" if item.passed else "0",
        )
    ).encode("utf-8")
    return hashlib.sha256(b"oma:evidence:v1\0" + payload).hexdigest()


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
            ValidationDecision.ACCEPT if parsed.decision is IdentityDecision.ALLOW else ValidationDecision.BLOCK,
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
            ValidationDecision.ACCEPT if identity.decision is IdentityDecision.ALLOW else ValidationDecision.BLOCK,
            identity.reasons,
        )
    )

    scope = evaluate_scope(pipeline_input.scope_policy, pipeline_input.transitions)
    scope_decision = {
        ScopeDecision.ALLOW: ValidationDecision.ACCEPT,
        ScopeDecision.REVIEW: ValidationDecision.NOT_DONE,
        ScopeDecision.BLOCK: ValidationDecision.BLOCK,
    }[scope.decision]
    observations.append(_observation("scope_integrity", scope_decision, scope.reasons))

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
    observations.append(_observation("authority_capability", authority_decision, authority.reasons))

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
    observations.append(_observation("trust_temporal", trust_decision, trust.reasons))

    observations.append(_observation("policy_bundle", ValidationDecision.NOT_DONE, ("policy_bundle_not_implemented",)))
    observations.append(_observation("snapshot_freshness", ValidationDecision.NOT_DONE, ("snapshot_freshness_not_implemented",)))

    if pipeline_input.provenance_policy is None or pipeline_input.provenance_nodes is None:
        observations.append(_observation("provenance", ValidationDecision.NOT_DONE, ("provenance_missing",)))
    else:
        evidence_digests = {
            item.evidence_id: _evidence_payload_digest(item)
            for item in pipeline_input.evidence
        }
        provenance = evaluate_provenance(
            pipeline_input.provenance_policy,
            pipeline_input.provenance_nodes,
            subject_id=pipeline_input.acceptance_context.subject_id,
            subject_state_id=pipeline_input.acceptance_context.subject_state_id,
            verification_context_id=pipeline_input.acceptance_context.verification_context_id,
            policy_bundle_id=pipeline_input.acceptance_context.policy_bundle_id,
            required_evidence_ids=frozenset(evidence_digests),
            required_evidence_digests=evidence_digests,
        )
        provenance_reasons = provenance.reasons
        provenance_decision = (
            ValidationDecision.ACCEPT
            if provenance.decision is ProvenanceDecision.ALLOW
            else ValidationDecision.BLOCK
        )
        if (
            provenance.decision is ProvenanceDecision.ALLOW
            and pipeline_input.snapshot.evidence_root != provenance.provenance_root
        ):
            provenance_decision = ValidationDecision.BLOCK
            provenance_reasons = ("snapshot_provenance_root_mismatch",)
        observations.append(_observation("provenance", provenance_decision, provenance_reasons))

    if pipeline_input.expected_obligation_manifest is None or pipeline_input.presented_obligation_manifest is None:
        observations.append(_observation("obligation_integrity", ValidationDecision.NOT_DONE, ("obligation_manifest_missing",)))
    else:
        obligation = evaluate_obligation_manifest(
            pipeline_input.expected_obligation_manifest,
            pipeline_input.presented_obligation_manifest,
            acceptance_required_obligations=pipeline_input.acceptance_context.required_obligations,
        )
        obligation_reasons = obligation.reasons
        obligation_decision = (
            ValidationDecision.ACCEPT
            if obligation.decision is ObligationDecision.ALLOW
            else ValidationDecision.BLOCK
        )
        if (
            obligation.decision is ObligationDecision.ALLOW
            and pipeline_input.snapshot.obligation_root != obligation.obligation_root
        ):
            obligation_decision = ValidationDecision.BLOCK
            obligation_reasons = ("snapshot_obligation_root_mismatch",)
        observations.append(_observation("obligation_integrity", obligation_decision, obligation_reasons))

    acceptance = evaluate_acceptance(pipeline_input.acceptance_context, pipeline_input.evidence)
    acceptance_decision = {
        AcceptanceDecision.ACCEPT: ValidationDecision.ACCEPT,
        AcceptanceDecision.NOT_DONE: ValidationDecision.NOT_DONE,
        AcceptanceDecision.BLOCK: ValidationDecision.BLOCK,
    }[acceptance.decision]
    observations.append(_observation("evidence_qualification", acceptance_decision, acceptance.reasons))

    observations.append(_observation("aggregation", ValidationDecision.NOT_DONE, ("aggregation_not_implemented",)))

    retry = evaluate_retry_domain(pipeline_input.retry_policy, pipeline_input.retry_domain, pipeline_input.retry_events)
    observations.append(
        _observation(
            "retry_recovery",
            ValidationDecision.ACCEPT if retry.decision is RetryDecision.ALLOW else ValidationDecision.BLOCK,
            retry.reasons,
        )
    )

    observations.append(_observation("terminal_barrier", ValidationDecision.NOT_DONE, ("terminal_barrier_not_implemented",)))

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
    observations.append(_observation("commit_authorization", commit_decision, commit.reasons))

    observations.append(_observation("atomic_commit", ValidationDecision.NOT_DONE, ("atomic_commit_not_implemented",)))

    result = evaluate_validation_graph(canonical_validation_graph(), observations)
    return ComposedPipelineResult(result=result, observations=tuple(observations))

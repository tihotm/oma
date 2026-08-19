from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .acceptance import AcceptanceDecision, evaluate_acceptance
from .aggregation import AggregationDecision, AggregationItem, evaluate_aggregation
from .authority import AuthorityDecision, evaluate_authority
from .commit import CommitDecision, evaluate_commit
from .identity import IdentityDecision, make_typed_identity, strict_parse_json
from .obligation import ObligationDecision, evaluate_obligation_manifest, obligation_root
from .policy import (
    PolicyBinding,
    PolicyBundle,
    PolicyBundleDecision,
    evaluate_policy_bundle,
    policy_object_root,
)
from .provenance import ProvenanceDecision, evaluate_provenance
from .retry import RetryDecision, evaluate_retry_domain
from .scope import ScopeDecision, evaluate_scope
from .terminal import TerminalDecision, canonical_terminal_policy, evaluate_terminal_barrier
from .trust import TrustDecision, evaluate_trust
from .validation import (
    ValidationDecision,
    ValidationObservation,
    ValidationResult,
    canonical_validation_graph,
    evaluate_validation_graph,
)


_REQUIRED_POLICY_KINDS = frozenset(
    {
        "serialization",
        "identity",
        "scope",
        "authority",
        "trust",
        "obligation",
        "provenance",
        "aggregation",
        "retry",
        "termination",
    }
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
    aggregation_policy: Any | None = None
    expected_policy_bundle: Any | None = None
    termination_policy_id: str | None = None
    terminal_action: str = "COMMIT"


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


def _presented_policy_bundle(pipeline_input: ComposedPipelineInput) -> PolicyBundle | None:
    if (
        pipeline_input.expected_policy_bundle is None
        or pipeline_input.termination_policy_id is None
        or pipeline_input.presented_obligation_manifest is None
        or pipeline_input.provenance_policy is None
        or pipeline_input.aggregation_policy is None
    ):
        return None

    termination_policy = canonical_terminal_policy(pipeline_input.termination_policy_id)
    bindings = (
        PolicyBinding(
            "serialization",
            pipeline_input.schema.schema_id,
            policy_object_root("serialization", pipeline_input.schema),
        ),
        PolicyBinding(
            "identity",
            pipeline_input.identity_policy.identity_policy_id,
            policy_object_root("identity", pipeline_input.identity_policy),
        ),
        PolicyBinding(
            "scope",
            pipeline_input.scope_policy.scope_policy_id,
            policy_object_root("scope", pipeline_input.scope_policy),
        ),
        PolicyBinding(
            "authority",
            pipeline_input.authority_context.authority_context_id,
            policy_object_root("authority", pipeline_input.authority_context),
        ),
        PolicyBinding(
            "trust",
            pipeline_input.trust_context.temporal_context_id,
            policy_object_root("trust", pipeline_input.trust_roots),
        ),
        PolicyBinding(
            "obligation",
            pipeline_input.presented_obligation_manifest.obligation_set_id,
            obligation_root(pipeline_input.presented_obligation_manifest),
        ),
        PolicyBinding(
            "provenance",
            pipeline_input.provenance_policy.provenance_policy_id,
            policy_object_root("provenance", pipeline_input.provenance_policy),
        ),
        PolicyBinding(
            "aggregation",
            pipeline_input.aggregation_policy.aggregation_policy_id,
            policy_object_root("aggregation", pipeline_input.aggregation_policy),
        ),
        PolicyBinding(
            "retry",
            pipeline_input.retry_policy.retry_policy_id,
            policy_object_root("retry", pipeline_input.retry_policy),
        ),
        PolicyBinding(
            "termination",
            termination_policy.termination_policy_id,
            policy_object_root("termination", termination_policy),
        ),
    )
    return PolicyBundle(
        policy_bundle_id=pipeline_input.expected_policy_bundle.policy_bundle_id,
        bundle_epoch=pipeline_input.expected_policy_bundle.bundle_epoch,
        bindings=bindings,
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

    presented_bundle = _presented_policy_bundle(pipeline_input)
    if pipeline_input.expected_policy_bundle is None or presented_bundle is None:
        observations.append(
            _observation(
                "policy_bundle",
                ValidationDecision.NOT_DONE,
                ("policy_bundle_missing",),
            )
        )
    else:
        bound_bundle_ids = (
            pipeline_input.acceptance_context.policy_bundle_id,
            pipeline_input.snapshot.policy_bundle_id,
            pipeline_input.commit_state.policy_bundle_id,
            *(item.policy_bundle_id for item in pipeline_input.evidence),
        )
        policy_bundle = evaluate_policy_bundle(
            pipeline_input.expected_policy_bundle,
            presented_bundle,
            required_policy_kinds=_REQUIRED_POLICY_KINDS,
            bound_policy_bundle_ids=bound_bundle_ids,
        )
        bundle_reasons = policy_bundle.reasons
        bundle_decision = (
            ValidationDecision.ACCEPT
            if policy_bundle.decision is PolicyBundleDecision.ALLOW
            else ValidationDecision.BLOCK
        )
        if policy_bundle.decision is PolicyBundleDecision.ALLOW:
            if pipeline_input.snapshot.policy_bundle_root != policy_bundle.policy_bundle_root:
                bundle_decision = ValidationDecision.BLOCK
                bundle_reasons = ("snapshot_policy_bundle_root_mismatch",)
            elif pipeline_input.commit_state.policy_bundle_root != policy_bundle.policy_bundle_root:
                bundle_decision = ValidationDecision.BLOCK
                bundle_reasons = ("current_policy_bundle_root_mismatch",)
        observations.append(_observation("policy_bundle", bundle_decision, bundle_reasons))

    observations.append(_observation("snapshot_freshness", ValidationDecision.NOT_DONE, ("snapshot_freshness_not_implemented",)))

    evidence_digests = {
        item.evidence_id: _evidence_payload_digest(item)
        for item in pipeline_input.evidence
    }

    if pipeline_input.provenance_policy is None or pipeline_input.provenance_nodes is None:
        observations.append(_observation("provenance", ValidationDecision.NOT_DONE, ("provenance_missing",)))
    else:
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

    if pipeline_input.aggregation_policy is None:
        observations.append(_observation("aggregation", ValidationDecision.NOT_DONE, ("aggregation_policy_missing",)))
    else:
        current_pair_id = pipeline_input.retry_domain.pair_id
        current_run_id = pipeline_input.retry_events[-1].run_id if pipeline_input.retry_events else ""
        aggregation_items = tuple(
            AggregationItem(
                evidence_id=item.evidence_id,
                payload_digest=evidence_digests[item.evidence_id],
                subject_id=item.subject_id,
                subject_state_id=item.subject_state_id,
                verification_context_id=item.verification_context_id,
                policy_bundle_id=item.policy_bundle_id,
                pair_id=current_pair_id,
                run_id=current_run_id,
                passed=item.passed,
            )
            for item in pipeline_input.evidence
        )
        aggregation = evaluate_aggregation(pipeline_input.aggregation_policy, aggregation_items)
        aggregation_decision = {
            AggregationDecision.ALLOW: ValidationDecision.ACCEPT,
            AggregationDecision.NOT_DONE: ValidationDecision.NOT_DONE,
            AggregationDecision.BLOCK: ValidationDecision.BLOCK,
        }[aggregation.decision]
        observations.append(_observation("aggregation", aggregation_decision, aggregation.reasons))

    retry = evaluate_retry_domain(pipeline_input.retry_policy, pipeline_input.retry_domain, pipeline_input.retry_events)
    observations.append(
        _observation(
            "retry_recovery",
            ValidationDecision.ACCEPT if retry.decision is RetryDecision.ALLOW else ValidationDecision.BLOCK,
            retry.reasons,
        )
    )

    if pipeline_input.termination_policy_id is None:
        observations.append(_observation("terminal_barrier", ValidationDecision.NOT_DONE, ("termination_policy_missing",)))
    else:
        terminal = evaluate_terminal_barrier(
            canonical_terminal_policy(pipeline_input.termination_policy_id),
            tuple(observations),
            requested_action=pipeline_input.terminal_action,
        )
        terminal_decision = {
            TerminalDecision.ALLOW: ValidationDecision.ACCEPT,
            TerminalDecision.NOT_DONE: ValidationDecision.NOT_DONE,
            TerminalDecision.STALE: ValidationDecision.STALE,
            TerminalDecision.BLOCK: ValidationDecision.BLOCK,
        }[terminal.decision]
        observations.append(_observation("terminal_barrier", terminal_decision, terminal.reasons))

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

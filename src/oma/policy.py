from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum, StrEnum
import hashlib
import json
from typing import Iterable


class PolicyBundleDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class PolicyBinding:
    policy_kind: str
    policy_id: str
    policy_root: str


@dataclass(frozen=True, slots=True)
class PolicyBundle:
    policy_bundle_id: str
    bundle_epoch: int
    bindings: tuple[PolicyBinding, ...]


@dataclass(frozen=True, slots=True)
class PolicyBundleResult:
    decision: PolicyBundleDecision
    reasons: tuple[str, ...] = ()
    policy_bundle_root: str | None = None


def _canonical_value(value):
    if is_dataclass(value):
        return {key: _canonical_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (set, frozenset)):
        normalized = [_canonical_value(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    return value


def policy_object_root(policy_kind: str, value) -> str:
    if not policy_kind:
        raise ValueError("policy_kind must be non-empty")
    canonical = json.dumps(
        _canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(
        ("oma:policy-object:v1\0" + policy_kind + "\0" + canonical).encode("utf-8")
    ).hexdigest()


def policy_bundle_root(bundle: PolicyBundle) -> str:
    rows = [
        "\0".join((item.policy_kind, item.policy_id, item.policy_root))
        for item in sorted(bundle.bindings, key=lambda item: item.policy_kind)
    ]
    payload = (
        "oma:policy-bundle:v1\0"
        + bundle.policy_bundle_id
        + "\0"
        + str(bundle.bundle_epoch)
        + "\n"
        + "\n".join(rows)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evaluate_policy_bundle(
    expected: PolicyBundle,
    presented: PolicyBundle,
    *,
    required_policy_kinds: frozenset[str],
    bound_policy_bundle_ids: Iterable[str] = (),
) -> PolicyBundleResult:
    if (
        not expected.policy_bundle_id
        or expected.bundle_epoch < 0
        or not expected.bindings
        or not required_policy_kinds
    ):
        return PolicyBundleResult(
            PolicyBundleDecision.BLOCK,
            ("invalid_expected_policy_bundle",),
        )

    def validate(bundle: PolicyBundle, label: str) -> str | None:
        if not bundle.policy_bundle_id or bundle.bundle_epoch < 0 or not bundle.bindings:
            return f"invalid_{label}_policy_bundle"
        kinds = [item.policy_kind for item in bundle.bindings]
        if not all(kinds) or len(kinds) != len(set(kinds)):
            return f"invalid_or_duplicate_{label}_policy_kind"
        if any(not item.policy_id or not item.policy_root for item in bundle.bindings):
            return f"invalid_{label}_policy_binding"
        if set(kinds) != set(required_policy_kinds):
            return f"{label}_policy_kind_set_mismatch"
        return None

    for bundle, label in ((expected, "expected"), (presented, "presented")):
        error = validate(bundle, label)
        if error:
            return PolicyBundleResult(PolicyBundleDecision.BLOCK, (error,))

    bound_ids = tuple(bound_policy_bundle_ids)
    if any(not value for value in bound_ids):
        return PolicyBundleResult(
            PolicyBundleDecision.BLOCK,
            ("empty_bound_policy_bundle_id",),
        )
    if any(value != expected.policy_bundle_id for value in bound_ids):
        return PolicyBundleResult(
            PolicyBundleDecision.BLOCK,
            ("policy_bundle_binding_mismatch",),
        )

    if presented.policy_bundle_id != expected.policy_bundle_id:
        return PolicyBundleResult(
            PolicyBundleDecision.BLOCK,
            ("policy_bundle_id_mismatch",),
        )
    if presented.bundle_epoch != expected.bundle_epoch:
        return PolicyBundleResult(
            PolicyBundleDecision.BLOCK,
            ("policy_bundle_epoch_mismatch",),
        )

    expected_by_kind = {item.policy_kind: item for item in expected.bindings}
    presented_by_kind = {item.policy_kind: item for item in presented.bindings}
    reasons: list[str] = []
    for kind in sorted(required_policy_kinds):
        left = expected_by_kind[kind]
        right = presented_by_kind[kind]
        if right.policy_id != left.policy_id:
            reasons.append(f"policy_id_mismatch:{kind}")
        if right.policy_root != left.policy_root:
            reasons.append(f"policy_root_mismatch:{kind}")
    if reasons:
        return PolicyBundleResult(PolicyBundleDecision.BLOCK, tuple(reasons))

    return PolicyBundleResult(
        PolicyBundleDecision.ALLOW,
        (),
        policy_bundle_root(expected),
    )

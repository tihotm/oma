from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import math
import unicodedata
from typing import Any


class IdentityDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class IdentityPolicy:
    identity_policy_id: str
    case_sensitive: bool = False
    unicode_form: str = "NFKC"


@dataclass(frozen=True, slots=True)
class TypedIdentity:
    namespace: str
    canonical_id: str


@dataclass(frozen=True, slots=True)
class IdentityResult:
    decision: IdentityDecision
    identity: TypedIdentity | None = None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StrictSchema:
    schema_id: str
    schema_version: int
    required_fields: frozenset[str]
    optional_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ParseResult:
    decision: IdentityDecision
    value: dict[str, Any] | None = None
    reasons: tuple[str, ...] = ()


def canonicalize_identifier(value: str, policy: IdentityPolicy) -> str | None:
    if not policy.identity_policy_id or policy.unicode_form not in {"NFC", "NFKC"}:
        return None
    if not isinstance(value, str) or not value:
        return None
    normalized = unicodedata.normalize(policy.unicode_form, value)
    if any(unicodedata.category(ch).startswith("C") for ch in normalized):
        return None
    normalized = normalized if policy.case_sensitive else normalized.casefold()
    if not normalized or normalized != normalized.strip():
        return None
    return normalized


def make_typed_identity(namespace: str, raw_id: str, policy: IdentityPolicy) -> IdentityResult:
    canonical_namespace = canonicalize_identifier(namespace, policy)
    canonical_id = canonicalize_identifier(raw_id, policy)
    if canonical_namespace is None or canonical_id is None:
        return IdentityResult(IdentityDecision.BLOCK, reasons=("invalid_identity",))
    return IdentityResult(
        IdentityDecision.ALLOW,
        TypedIdentity(canonical_namespace, canonical_id),
    )


def identity_digest(identity: TypedIdentity) -> str:
    payload = f"oma:identity:v1\0{identity.namespace}\0{identity.canonical_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def content_digest(payload: bytes) -> str:
    return hashlib.sha256(b"oma:content:v1\0" + payload).hexdigest()


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_field:{key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise ValueError(f"non_finite_number:{value}")


def strict_parse_json(text: str, schema: StrictSchema) -> ParseResult:
    if not schema.schema_id or schema.schema_version < 1:
        return ParseResult(IdentityDecision.BLOCK, reasons=("invalid_schema",))
    if not isinstance(text, str) or not text:
        return ParseResult(IdentityDecision.BLOCK, reasons=("empty_input",))
    try:
        decoder = json.JSONDecoder(
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
        value, end = decoder.raw_decode(text)
    except (json.JSONDecodeError, ValueError) as exc:
        return ParseResult(IdentityDecision.BLOCK, reasons=(f"parse_error:{exc}",))

    if text[end:].strip():
        return ParseResult(IdentityDecision.BLOCK, reasons=("trailing_data",))
    if not isinstance(value, dict):
        return ParseResult(IdentityDecision.BLOCK, reasons=("root_not_object",))

    allowed = schema.required_fields | schema.optional_fields
    unknown = sorted(set(value) - allowed)
    if unknown:
        return ParseResult(
            IdentityDecision.BLOCK,
            reasons=tuple(f"unknown_field:{field}" for field in unknown),
        )
    missing = sorted(schema.required_fields - set(value))
    if missing:
        return ParseResult(
            IdentityDecision.BLOCK,
            reasons=tuple(f"missing_field:{field}" for field in missing),
        )

    def validate_numbers(node: Any) -> bool:
        if isinstance(node, bool) or node is None or isinstance(node, str):
            return True
        if isinstance(node, int):
            return -(2**53 - 1) <= node <= (2**53 - 1)
        if isinstance(node, float):
            return math.isfinite(node) and node.is_integer() and abs(node) <= (2**53 - 1)
        if isinstance(node, list):
            return all(validate_numbers(x) for x in node)
        if isinstance(node, dict):
            return all(validate_numbers(v) for v in node.values())
        return False

    if not validate_numbers(value):
        return ParseResult(IdentityDecision.BLOCK, reasons=("ambiguous_numeric_value",))

    return ParseResult(IdentityDecision.ALLOW, value=value)

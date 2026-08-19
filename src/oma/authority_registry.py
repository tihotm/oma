from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
import sqlite3

from .authority import (
    AuthorityContext,
    AuthorityDecision,
    AuthorityRequest,
    Capability,
    evaluate_authority,
)


class AuthorityRegistryDecision(StrEnum):
    WRITTEN = "WRITTEN"
    CONFLICT = "CONFLICT"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class AuthorityRegistryResult:
    decision: AuthorityRegistryDecision
    reasons: tuple[str, ...] = ()
    capability: Capability | None = None


def _frame(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(8, "big") + raw


def authority_context_digest(context: AuthorityContext) -> str:
    payload = b"".join(
        (
            _frame(context.authority_context_id),
            _frame(str(context.authority_epoch)),
            _frame("\n".join(sorted(context.trusted_issuers))),
        )
    )
    return hashlib.sha256(b"oma:authority-context:v1\0" + payload).hexdigest()


def ensure_authority_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS authority_contexts (
            authority_context_id TEXT PRIMARY KEY,
            authority_epoch INTEGER NOT NULL CHECK (authority_epoch >= 0),
            trusted_issuers_digest TEXT NOT NULL,
            context_digest TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS authority_capabilities (
            authority_context_id TEXT NOT NULL,
            capability_id TEXT NOT NULL,
            issuer TEXT NOT NULL,
            holder TEXT NOT NULL,
            actions TEXT NOT NULL,
            targets TEXT NOT NULL,
            scopes TEXT NOT NULL,
            authority_epoch INTEGER NOT NULL CHECK (authority_epoch >= 0),
            not_before_epoch INTEGER NOT NULL CHECK (not_before_epoch >= 0),
            expires_epoch INTEGER NOT NULL,
            parent_capability_id TEXT,
            PRIMARY KEY (authority_context_id, capability_id),
            FOREIGN KEY (authority_context_id)
                REFERENCES authority_contexts(authority_context_id)
        )
        """
    )


def _set_encode(values: frozenset[str]) -> str:
    # IDs/actions containing newlines are not accepted at this authoritative
    # registry boundary; this avoids an ambiguous storage encoding.
    return "\n".join(sorted(values))


def _set_decode(value: str) -> frozenset[str]:
    return frozenset() if value == "" else frozenset(value.split("\n"))


def _valid_atom(value: str) -> bool:
    return bool(value) and "\n" not in value and "\x00" not in value


def _valid_capability_storage(capability: Capability) -> bool:
    atoms = (
        capability.capability_id,
        capability.issuer,
        capability.holder,
        *capability.actions,
        *capability.targets,
        *capability.scopes,
    )
    if capability.parent_capability_id is not None:
        atoms = (*atoms, capability.parent_capability_id)
    return (
        all(_valid_atom(value) for value in atoms)
        and bool(capability.actions)
        and bool(capability.targets)
        and bool(capability.scopes)
        and capability.authority_epoch >= 0
        and capability.not_before_epoch >= 0
        and capability.expires_epoch >= capability.not_before_epoch
    )


def _capability_from_row(row: tuple[object, ...]) -> Capability:
    return Capability(
        capability_id=str(row[0]),
        issuer=str(row[1]),
        holder=str(row[2]),
        actions=_set_decode(str(row[3])),
        targets=_set_decode(str(row[4])),
        scopes=_set_decode(str(row[5])),
        authority_epoch=int(row[6]),
        not_before_epoch=int(row[7]),
        expires_epoch=int(row[8]),
        parent_capability_id=None if row[9] is None else str(row[9]),
    )


def load_authority_capabilities_from_connection(
    conn: sqlite3.Connection,
    context: AuthorityContext,
) -> tuple[Capability, ...] | None:
    ensure_authority_schema(conn)
    row = conn.execute(
        """
        SELECT authority_epoch, context_digest
        FROM authority_contexts
        WHERE authority_context_id = ?
        """,
        (context.authority_context_id,),
    ).fetchone()
    if row is None:
        return None
    if int(row[0]) != context.authority_epoch or str(row[1]) != authority_context_digest(context):
        return None
    rows = conn.execute(
        """
        SELECT capability_id, issuer, holder, actions, targets, scopes,
               authority_epoch, not_before_epoch, expires_epoch,
               parent_capability_id
        FROM authority_capabilities
        WHERE authority_context_id = ?
        ORDER BY capability_id
        """,
        (context.authority_context_id,),
    ).fetchall()
    return tuple(_capability_from_row(tuple(row)) for row in rows)


class SQLiteAuthorityRegistry:
    """Durable local issuance boundary for capabilities.

    This closes caller fabrication at the supported SQLite trust boundary. It
    does not claim cryptographic issuer authenticity against a hostile process;
    that remains a separate trust-root/key problem.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as conn:
            ensure_authority_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize_context(
        self,
        context: AuthorityContext,
        root_capabilities: tuple[Capability, ...],
    ) -> AuthorityRegistryResult:
        if (
            not context.authority_context_id
            or context.authority_epoch < 0
            or not context.trusted_issuers
            or not root_capabilities
        ):
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.BLOCK,
                ("invalid_authority_registry_context",),
            )
        ids = [cap.capability_id for cap in root_capabilities]
        if len(ids) != len(set(ids)):
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.BLOCK,
                ("duplicate_authority_registry_capability",),
            )
        for cap in root_capabilities:
            if (
                not _valid_capability_storage(cap)
                or cap.parent_capability_id is not None
                or cap.issuer not in context.trusted_issuers
                or cap.issuer == cap.holder
                or cap.authority_epoch != context.authority_epoch
            ):
                return AuthorityRegistryResult(
                    AuthorityRegistryDecision.BLOCK,
                    ("invalid_authority_registry_root",),
                )

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM authority_contexts WHERE authority_context_id = ?",
                (context.authority_context_id,),
            ).fetchone() is not None:
                conn.rollback()
                return AuthorityRegistryResult(
                    AuthorityRegistryDecision.CONFLICT,
                    ("authority_context_already_initialized",),
                )
            trusted_digest = hashlib.sha256(
                b"oma:trusted-issuers:v1\0"
                + b"".join(_frame(value) for value in sorted(context.trusted_issuers))
            ).hexdigest()
            conn.execute(
                """
                INSERT INTO authority_contexts (
                    authority_context_id, authority_epoch,
                    trusted_issuers_digest, context_digest
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    context.authority_context_id,
                    context.authority_epoch,
                    trusted_digest,
                    authority_context_digest(context),
                ),
            )
            for cap in root_capabilities:
                self._insert_capability(conn, context.authority_context_id, cap)
            conn.commit()
            return AuthorityRegistryResult(AuthorityRegistryDecision.WRITTEN)
        except sqlite3.IntegrityError:
            conn.rollback()
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.CONFLICT,
                ("authority_registry_integrity_conflict",),
            )
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.BLOCK,
                (f"sqlite_authority_registry_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def issue(
        self,
        context: AuthorityContext,
        capability: Capability,
    ) -> AuthorityRegistryResult:
        if not _valid_capability_storage(capability):
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.BLOCK,
                ("invalid_authority_registry_capability",),
            )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = load_authority_capabilities_from_connection(conn, context)
            if existing is None or not existing:
                conn.rollback()
                return AuthorityRegistryResult(
                    AuthorityRegistryDecision.BLOCK,
                    ("authority_context_not_authoritative",),
                )
            request = AuthorityRequest(
                actor=capability.holder,
                action=sorted(capability.actions)[0],
                target=sorted(capability.targets)[0],
                scope=sorted(capability.scopes)[0],
                capability_id=capability.capability_id,
            )
            result = evaluate_authority(context, (*existing, capability), request)
            if result.decision is not AuthorityDecision.ALLOW:
                conn.rollback()
                return AuthorityRegistryResult(
                    AuthorityRegistryDecision.BLOCK,
                    result.reasons,
                )
            self._insert_capability(conn, context.authority_context_id, capability)
            conn.commit()
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.WRITTEN,
                (),
                capability,
            )
        except sqlite3.IntegrityError:
            conn.rollback()
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.CONFLICT,
                ("authority_registry_integrity_conflict",),
            )
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return AuthorityRegistryResult(
                AuthorityRegistryDecision.BLOCK,
                (f"sqlite_authority_registry_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def get(self, context: AuthorityContext) -> tuple[Capability, ...] | None:
        with self._connect() as conn:
            return load_authority_capabilities_from_connection(conn, context)

    def _insert_capability(
        self,
        conn: sqlite3.Connection,
        authority_context_id: str,
        capability: Capability,
    ) -> None:
        conn.execute(
            """
            INSERT INTO authority_capabilities (
                authority_context_id, capability_id, issuer, holder,
                actions, targets, scopes, authority_epoch, not_before_epoch,
                expires_epoch, parent_capability_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                authority_context_id,
                capability.capability_id,
                capability.issuer,
                capability.holder,
                _set_encode(capability.actions),
                _set_encode(capability.targets),
                _set_encode(capability.scopes),
                capability.authority_epoch,
                capability.not_before_epoch,
                capability.expires_epoch,
                capability.parent_capability_id,
            ),
        )

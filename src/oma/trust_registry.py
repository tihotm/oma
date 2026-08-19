from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
import sqlite3

from .trust import SignedArtifact, TrustContext, TrustDecision, TrustRoot, evaluate_trust


class TrustRegistryDecision(StrEnum):
    WRITTEN = "WRITTEN"
    CONFLICT = "CONFLICT"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class TrustRegistryResult:
    decision: TrustRegistryDecision
    reasons: tuple[str, ...] = ()
    artifact: SignedArtifact | None = None


def _frame(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(8, "big") + raw


def trust_roots_digest(roots: tuple[TrustRoot, ...]) -> str:
    rows: list[bytes] = []
    for root in sorted(roots, key=lambda item: item.root_id):
        rows.append(
            b"".join(
                _frame(value)
                for value in (
                    root.root_id,
                    str(root.trust_epoch),
                    root.status.value,
                    root.parent_root_id or "",
                    str(root.activated_epoch),
                    "" if root.retired_epoch is None else str(root.retired_epoch),
                    "" if root.compromised_epoch is None else str(root.compromised_epoch),
                )
            )
        )
    return hashlib.sha256(b"oma:trust-roots:v1\0" + b"".join(rows)).hexdigest()


def ensure_trust_registry_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_artifacts (
            temporal_context_id TEXT NOT NULL,
            roots_digest TEXT NOT NULL,
            artifact_id TEXT PRIMARY KEY,
            issuer_root_id TEXT NOT NULL,
            trust_epoch INTEGER NOT NULL CHECK (trust_epoch >= 0),
            authority_epoch INTEGER NOT NULL CHECK (authority_epoch >= 0),
            logical_epoch INTEGER NOT NULL CHECK (logical_epoch >= 0),
            state_version INTEGER NOT NULL CHECK (state_version >= 0),
            issued_epoch INTEGER NOT NULL CHECK (issued_epoch >= 0),
            expires_epoch INTEGER NOT NULL
        )
        """
    )


def _artifact_from_row(row: tuple[object, ...]) -> SignedArtifact:
    return SignedArtifact(
        artifact_id=str(row[0]),
        issuer_root_id=str(row[1]),
        trust_epoch=int(row[2]),
        authority_epoch=int(row[3]),
        logical_epoch=int(row[4]),
        state_version=int(row[5]),
        issued_epoch=int(row[6]),
        expires_epoch=int(row[7]),
    )


def load_trust_artifact_from_connection(
    conn: sqlite3.Connection,
    context: TrustContext,
    roots: tuple[TrustRoot, ...],
    artifact_id: str,
) -> SignedArtifact | None:
    ensure_trust_registry_schema(conn)
    if not artifact_id:
        return None
    row = conn.execute(
        """
        SELECT artifact_id, issuer_root_id, trust_epoch, authority_epoch,
               logical_epoch, state_version, issued_epoch, expires_epoch,
               temporal_context_id, roots_digest
        FROM trust_artifacts WHERE artifact_id = ?
        """,
        (artifact_id,),
    ).fetchone()
    if row is None:
        return None
    if str(row[8]) != context.temporal_context_id:
        return None
    if str(row[9]) != trust_roots_digest(roots):
        return None
    return _artifact_from_row(tuple(row[:8]))


class SQLiteTrustArtifactRegistry:
    """Durable local issuance registry for trust artifacts.

    Registration is a trusted local control-plane operation. Durable terminal
    execution accepts only artifacts previously registered against the exact
    temporal context ID and trust-root set. This closes caller object
    fabrication locally but is not a cryptographic signature scheme.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as conn:
            ensure_trust_registry_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def register(
        self,
        context: TrustContext,
        roots: tuple[TrustRoot, ...],
        artifact: SignedArtifact,
    ) -> TrustRegistryResult:
        result = evaluate_trust(context, roots, artifact)
        if result.decision is not TrustDecision.ALLOW:
            return TrustRegistryResult(
                TrustRegistryDecision.BLOCK,
                result.reasons,
            )
        if "\x00" in artifact.artifact_id or "\n" in artifact.artifact_id:
            return TrustRegistryResult(
                TrustRegistryDecision.BLOCK,
                ("invalid_trust_artifact_identifier",),
            )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO trust_artifacts (
                    temporal_context_id, roots_digest, artifact_id,
                    issuer_root_id, trust_epoch, authority_epoch, logical_epoch,
                    state_version, issued_epoch, expires_epoch
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.temporal_context_id,
                    trust_roots_digest(roots),
                    artifact.artifact_id,
                    artifact.issuer_root_id,
                    artifact.trust_epoch,
                    artifact.authority_epoch,
                    artifact.logical_epoch,
                    artifact.state_version,
                    artifact.issued_epoch,
                    artifact.expires_epoch,
                ),
            )
            conn.commit()
            return TrustRegistryResult(
                TrustRegistryDecision.WRITTEN,
                (),
                artifact,
            )
        except sqlite3.IntegrityError:
            conn.rollback()
            return TrustRegistryResult(
                TrustRegistryDecision.CONFLICT,
                ("trust_artifact_already_registered",),
            )
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return TrustRegistryResult(
                TrustRegistryDecision.BLOCK,
                (f"sqlite_trust_registry_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def get(
        self,
        context: TrustContext,
        roots: tuple[TrustRoot, ...],
        artifact_id: str,
    ) -> SignedArtifact | None:
        with self._connect() as conn:
            return load_trust_artifact_from_connection(
                conn,
                context,
                roots,
                artifact_id,
            )

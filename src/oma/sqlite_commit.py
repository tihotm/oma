from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING

from .authority import AuthorityContext, Capability
from .authority_registry import (
    ensure_authority_schema,
    load_authority_capabilities_from_connection,
)
from .commit import (
    AcceptanceSnapshot,
    CommitDecision,
    CommitState,
    CommitToken,
    evaluate_commit,
)
from .retry import RetryDomain, RetryEvent, RetryPolicy
from .retry_ledger import ensure_retry_schema, load_retry_events_from_connection
from .validation import (
    ValidationDecision,
    canonical_validation_graph,
    validation_observation_digest,
)

if TYPE_CHECKING:
    from .pipeline import ComposedPipelineInput


class DurableCommitDecision(StrEnum):
    COMMITTED = "COMMITTED"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    BLOCK = "BLOCK"


class SubjectStateDecision(StrEnum):
    WRITTEN = "WRITTEN"
    CONFLICT = "CONFLICT"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class DurableCommitResult:
    decision: DurableCommitDecision
    reasons: tuple[str, ...] = ()
    terminal_commit_id: str | None = None


@dataclass(frozen=True, slots=True)
class SubjectStateResult:
    decision: SubjectStateDecision
    reasons: tuple[str, ...] = ()
    state: CommitState | None = None


@dataclass(frozen=True, slots=True)
class DurableTerminalRecord:
    terminal_commit_id: str
    acceptance_snapshot_id: str
    subject_id: str
    terminal_epoch: int
    token_id: str
    subject_state_id: str
    policy_bundle_id: str
    policy_bundle_root: str | None
    obligation_root: str
    evidence_root: str
    ledger_head: str
    state_version: int
    validation_graph_id: str | None
    terminal_barrier_root: str | None
    precommit_closure_digest: str | None


def _state_values(state: CommitState) -> tuple[object, ...]:
    return (
        state.subject_id,
        state.subject_state_id,
        state.policy_bundle_id,
        state.policy_bundle_root,
        state.obligation_root,
        state.evidence_root,
        state.ledger_head,
        state.state_version,
        state.terminal_epoch,
    )


def _state_from_row(row: tuple[object, ...]) -> CommitState:
    return CommitState(
        subject_id=str(row[0]),
        subject_state_id=str(row[1]),
        policy_bundle_id=str(row[2]),
        policy_bundle_root=None if row[3] is None else str(row[3]),
        obligation_root=str(row[4]),
        evidence_root=str(row[5]),
        ledger_head=str(row[6]),
        state_version=int(row[7]),
        terminal_epoch=int(row[8]),
    )


def _valid_state(state: CommitState) -> bool:
    return bool(
        state.subject_id
        and state.subject_state_id
        and state.policy_bundle_id
        and state.obligation_root
        and state.evidence_root
        and state.ledger_head
        and state.state_version >= 0
        and state.terminal_epoch >= 0
    )


class SQLiteTerminalStore:
    """Authoritative state/history/capability CAS plus terminal commit.

    Subject state, retry history, and issued capabilities are re-read inside
    the same ``BEGIN IMMEDIATE`` transaction used to record terminalization.
    Public ``commit`` independently re-evaluates the composed closure against
    those authoritative facts before persisting the durable proof.
    """

    _STATE_SELECT = """
        SELECT subject_id, subject_state_id, policy_bundle_id,
               policy_bundle_root, obligation_root, evidence_root,
               ledger_head, state_version, terminal_epoch
        FROM subject_states WHERE subject_id = ?
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subject_states (
                    subject_id TEXT PRIMARY KEY,
                    subject_state_id TEXT NOT NULL,
                    policy_bundle_id TEXT NOT NULL,
                    policy_bundle_root TEXT,
                    obligation_root TEXT NOT NULL,
                    evidence_root TEXT NOT NULL,
                    ledger_head TEXT NOT NULL,
                    state_version INTEGER NOT NULL CHECK (state_version >= 0),
                    terminal_epoch INTEGER NOT NULL CHECK (terminal_epoch >= 0)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS terminal_commits (
                    terminal_commit_id TEXT PRIMARY KEY,
                    acceptance_snapshot_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    terminal_epoch INTEGER NOT NULL CHECK (terminal_epoch >= 0),
                    token_id TEXT NOT NULL UNIQUE,
                    subject_state_id TEXT NOT NULL,
                    policy_bundle_id TEXT NOT NULL,
                    policy_bundle_root TEXT,
                    obligation_root TEXT NOT NULL,
                    evidence_root TEXT NOT NULL,
                    ledger_head TEXT NOT NULL,
                    state_version INTEGER NOT NULL CHECK (state_version >= 0),
                    validation_graph_id TEXT,
                    terminal_barrier_root TEXT,
                    precommit_closure_digest TEXT,
                    UNIQUE(subject_id, terminal_epoch)
                )
                """
            )
            ensure_retry_schema(conn)
            ensure_authority_schema(conn)
            columns = {
                str(row[1]) for row in conn.execute("PRAGMA table_info(terminal_commits)")
            }
            for name in (
                "validation_graph_id",
                "terminal_barrier_root",
                "precommit_closure_digest",
            ):
                if name not in columns:
                    conn.execute(f"ALTER TABLE terminal_commits ADD COLUMN {name} TEXT")

    def initialize_subject_state(self, state: CommitState) -> SubjectStateResult:
        if not _valid_state(state):
            return SubjectStateResult(SubjectStateDecision.BLOCK, ("invalid_subject_state",))
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(self._STATE_SELECT, (state.subject_id,)).fetchone()
            if existing is not None:
                conn.rollback()
                return SubjectStateResult(
                    SubjectStateDecision.CONFLICT,
                    ("subject_state_already_initialized",),
                    _state_from_row(existing),
                )
            conn.execute(
                """
                INSERT INTO subject_states (
                    subject_id, subject_state_id, policy_bundle_id,
                    policy_bundle_root, obligation_root, evidence_root,
                    ledger_head, state_version, terminal_epoch
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _state_values(state),
            )
            conn.commit()
            return SubjectStateResult(SubjectStateDecision.WRITTEN, (), state)
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return SubjectStateResult(
                SubjectStateDecision.BLOCK,
                (f"sqlite_subject_state_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def advance_subject_state(
        self,
        expected_state_version: int,
        next_state: CommitState,
    ) -> SubjectStateResult:
        if expected_state_version < 0 or not _valid_state(next_state):
            return SubjectStateResult(
                SubjectStateDecision.BLOCK,
                ("invalid_subject_state_update",),
            )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(self._STATE_SELECT, (next_state.subject_id,)).fetchone()
            if row is None:
                conn.rollback()
                return SubjectStateResult(
                    SubjectStateDecision.CONFLICT,
                    ("subject_state_missing",),
                )
            current = _state_from_row(row)
            if current.state_version != expected_state_version:
                conn.rollback()
                return SubjectStateResult(
                    SubjectStateDecision.CONFLICT,
                    ("subject_state_version_conflict",),
                    current,
                )
            if next_state.state_version <= current.state_version:
                conn.rollback()
                return SubjectStateResult(
                    SubjectStateDecision.BLOCK,
                    ("subject_state_version_not_monotonic",),
                    current,
                )
            if next_state.terminal_epoch < current.terminal_epoch:
                conn.rollback()
                return SubjectStateResult(
                    SubjectStateDecision.BLOCK,
                    ("subject_terminal_epoch_rollback",),
                    current,
                )
            updated = conn.execute(
                """
                UPDATE subject_states
                SET subject_state_id = ?, policy_bundle_id = ?,
                    policy_bundle_root = ?, obligation_root = ?, evidence_root = ?,
                    ledger_head = ?, state_version = ?, terminal_epoch = ?
                WHERE subject_id = ? AND state_version = ?
                """,
                (
                    next_state.subject_state_id,
                    next_state.policy_bundle_id,
                    next_state.policy_bundle_root,
                    next_state.obligation_root,
                    next_state.evidence_root,
                    next_state.ledger_head,
                    next_state.state_version,
                    next_state.terminal_epoch,
                    next_state.subject_id,
                    expected_state_version,
                ),
            )
            if updated.rowcount != 1:
                conn.rollback()
                return SubjectStateResult(
                    SubjectStateDecision.CONFLICT,
                    ("subject_state_cas_conflict",),
                )
            conn.commit()
            return SubjectStateResult(SubjectStateDecision.WRITTEN, (), next_state)
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return SubjectStateResult(
                SubjectStateDecision.BLOCK,
                (f"sqlite_subject_state_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def get_subject_state(self, subject_id: str) -> CommitState | None:
        if not subject_id:
            return None
        with self._connect() as conn:
            row = conn.execute(self._STATE_SELECT, (subject_id,)).fetchone()
        return None if row is None else _state_from_row(row)

    def get_retry_events(
        self,
        policy: RetryPolicy,
        domain: RetryDomain,
    ) -> tuple[RetryEvent, ...] | None:
        with self._connect() as conn:
            return load_retry_events_from_connection(conn, domain, policy)

    def get_capabilities(
        self,
        context: AuthorityContext,
    ) -> tuple[Capability, ...] | None:
        with self._connect() as conn:
            return load_authority_capabilities_from_connection(conn, context)

    def commit(self, pipeline_input: ComposedPipelineInput) -> DurableCommitResult:
        """Atomically verify authoritative facts, closure and terminal write."""
        from .pipeline import evaluate_composed_pipeline

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                self._STATE_SELECT,
                (pipeline_input.snapshot.subject_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.BLOCK,
                    ("authoritative_subject_state_missing",),
                )

            authoritative_retry_events = load_retry_events_from_connection(
                conn,
                pipeline_input.retry_domain,
                pipeline_input.retry_policy,
            )
            if authoritative_retry_events is None or not authoritative_retry_events:
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.BLOCK,
                    ("authoritative_retry_history_missing",),
                )

            authoritative_capabilities = load_authority_capabilities_from_connection(
                conn,
                pipeline_input.authority_context,
            )
            if authoritative_capabilities is None or not authoritative_capabilities:
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.BLOCK,
                    ("authoritative_capabilities_missing",),
                )

            authoritative = _state_from_row(row)
            effective_input = replace(
                pipeline_input,
                commit_state=authoritative,
                retry_events=authoritative_retry_events,
                capabilities=authoritative_capabilities,
            )
            evaluated = evaluate_composed_pipeline(effective_input)
            prior = tuple(
                item for item in evaluated.observations
                if item.node_id != "atomic_commit"
            )
            if any(item.decision is ValidationDecision.BLOCK for item in prior):
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.BLOCK,
                    ("durable_boundary_prerequisite_blocked",),
                )
            if any(item.decision is ValidationDecision.STALE for item in prior):
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.STALE,
                    ("durable_boundary_prerequisite_stale",),
                )
            if any(item.decision is not ValidationDecision.ACCEPT for item in prior):
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.BLOCK,
                    ("durable_boundary_closure_incomplete",),
                )

            graph = canonical_validation_graph()
            precommit_digest = validation_observation_digest(
                graph,
                prior,
                domain="precommit",
            )
            terminal_observation = next(
                (item for item in prior if item.node_id == "terminal_barrier"),
                None,
            )
            if (
                precommit_digest is None
                or terminal_observation is None
                or terminal_observation.decision is not ValidationDecision.ACCEPT
                or not terminal_observation.evidence_root
            ):
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.BLOCK,
                    ("durable_closure_proof_invalid",),
                )

            preliminary = evaluate_commit(
                pipeline_input.snapshot,
                pipeline_input.commit_token,
                authoritative,
                terminal_commit_id=pipeline_input.terminal_commit_id,
            )
            if preliminary.decision is CommitDecision.BLOCK:
                conn.rollback()
                return DurableCommitResult(DurableCommitDecision.BLOCK, preliminary.reasons)
            if preliminary.decision is CommitDecision.STALE:
                conn.rollback()
                return DurableCommitResult(DurableCommitDecision.STALE, preliminary.reasons)
            if preliminary.decision is CommitDecision.CONFLICT:
                conn.rollback()
                return DurableCommitResult(DurableCommitDecision.CONFLICT, preliminary.reasons)

            existing_epoch = conn.execute(
                """
                SELECT terminal_commit_id
                FROM terminal_commits
                WHERE subject_id = ? AND terminal_epoch = ?
                """,
                (pipeline_input.snapshot.subject_id, pipeline_input.snapshot.terminal_epoch),
            ).fetchone()
            if existing_epoch is not None:
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.CONFLICT,
                    ("terminal_epoch_already_committed",),
                    existing_epoch[0],
                )

            replay = conn.execute(
                "SELECT terminal_commit_id FROM terminal_commits WHERE token_id = ?",
                (pipeline_input.commit_token.token_id,),
            ).fetchone()
            if replay is not None:
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.CONFLICT,
                    ("commit_token_replay",),
                    replay[0],
                )

            self._insert_terminal(
                conn,
                pipeline_input.snapshot,
                pipeline_input.commit_token,
                pipeline_input.terminal_commit_id,
                validation_graph_id=graph.validation_graph_id,
                terminal_barrier_root=terminal_observation.evidence_root,
                precommit_closure_digest=precommit_digest,
            )
            conn.commit()
            return DurableCommitResult(
                DurableCommitDecision.COMMITTED,
                (),
                pipeline_input.terminal_commit_id,
            )
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            return DurableCommitResult(
                DurableCommitDecision.CONFLICT,
                (f"sqlite_integrity_conflict:{type(exc).__name__}",),
            )
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return DurableCommitResult(
                DurableCommitDecision.BLOCK,
                (f"sqlite_database_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def _insert_terminal(
        self,
        conn: sqlite3.Connection,
        snapshot: AcceptanceSnapshot,
        token: CommitToken,
        terminal_commit_id: str,
        *,
        validation_graph_id: str | None = None,
        terminal_barrier_root: str | None = None,
        precommit_closure_digest: str | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO terminal_commits (
                terminal_commit_id, acceptance_snapshot_id, subject_id,
                terminal_epoch, token_id, subject_state_id, policy_bundle_id,
                policy_bundle_root, obligation_root, evidence_root,
                ledger_head, state_version, validation_graph_id,
                terminal_barrier_root, precommit_closure_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                terminal_commit_id,
                snapshot.acceptance_snapshot_id,
                snapshot.subject_id,
                snapshot.terminal_epoch,
                token.token_id,
                snapshot.subject_state_id,
                snapshot.policy_bundle_id,
                snapshot.policy_bundle_root,
                snapshot.obligation_root,
                snapshot.evidence_root,
                snapshot.ledger_head,
                snapshot.state_version,
                validation_graph_id,
                terminal_barrier_root,
                precommit_closure_digest,
            ),
        )

    def _commit_prevalidated(
        self,
        snapshot: AcceptanceSnapshot,
        token: CommitToken,
        current: CommitState,
        *,
        terminal_commit_id: str,
    ) -> DurableCommitResult:
        """SQL storage primitive for storage-level tests only."""
        preliminary = evaluate_commit(
            snapshot,
            token,
            current,
            terminal_commit_id=terminal_commit_id,
        )
        if preliminary.decision is CommitDecision.BLOCK:
            return DurableCommitResult(DurableCommitDecision.BLOCK, preliminary.reasons)
        if preliminary.decision is CommitDecision.STALE:
            return DurableCommitResult(DurableCommitDecision.STALE, preliminary.reasons)
        if preliminary.decision is CommitDecision.CONFLICT:
            return DurableCommitResult(DurableCommitDecision.CONFLICT, preliminary.reasons)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing_epoch = conn.execute(
                "SELECT terminal_commit_id FROM terminal_commits WHERE subject_id = ? AND terminal_epoch = ?",
                (snapshot.subject_id, snapshot.terminal_epoch),
            ).fetchone()
            if existing_epoch is not None:
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.CONFLICT,
                    ("terminal_epoch_already_committed",),
                    existing_epoch[0],
                )
            replay = conn.execute(
                "SELECT terminal_commit_id FROM terminal_commits WHERE token_id = ?",
                (token.token_id,),
            ).fetchone()
            if replay is not None:
                conn.rollback()
                return DurableCommitResult(
                    DurableCommitDecision.CONFLICT,
                    ("commit_token_replay",),
                    replay[0],
                )
            self._insert_terminal(conn, snapshot, token, terminal_commit_id)
            conn.commit()
            return DurableCommitResult(
                DurableCommitDecision.COMMITTED,
                (),
                terminal_commit_id,
            )
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            return DurableCommitResult(
                DurableCommitDecision.CONFLICT,
                (f"sqlite_integrity_conflict:{type(exc).__name__}",),
            )
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return DurableCommitResult(
                DurableCommitDecision.BLOCK,
                (f"sqlite_database_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def get(self, terminal_commit_id: str) -> DurableTerminalRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT terminal_commit_id, acceptance_snapshot_id, subject_id,
                       terminal_epoch, token_id, subject_state_id,
                       policy_bundle_id, policy_bundle_root, obligation_root,
                       evidence_root, ledger_head, state_version,
                       validation_graph_id, terminal_barrier_root,
                       precommit_closure_digest
                FROM terminal_commits WHERE terminal_commit_id = ?
                """,
                (terminal_commit_id,),
            ).fetchone()
        return None if row is None else DurableTerminalRecord(*row)

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM terminal_commits").fetchone()[0])

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING

from .commit import (
    AcceptanceSnapshot,
    CommitDecision,
    CommitState,
    CommitToken,
    evaluate_commit,
)
from .validation import ValidationDecision

if TYPE_CHECKING:
    from .pipeline import ComposedPipelineInput


class DurableCommitDecision(StrEnum):
    COMMITTED = "COMMITTED"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class DurableCommitResult:
    decision: DurableCommitDecision
    reasons: tuple[str, ...] = ()
    terminal_commit_id: str | None = None


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


class SQLiteTerminalStore:
    """Durable terminal store whose public commit boundary revalidates closure.

    The public ``commit`` method accepts the complete composed pipeline input and
    independently evaluates every prerequisite before entering the SQLite
    transaction. The SQL-only primitive is private so production callers cannot
    accidentally bypass authority, policy, provenance, aggregation, freshness,
    retry or terminal-barrier checks by supplying only snapshot/token objects.

    SQLite is configured for WAL + FULL synchronous durability. One committed
    row represents terminal-record creation and token consumption atomically,
    with uniqueness constraints enforcing single-use tokens and one terminal
    record per ``(subject_id, terminal_epoch)``.
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
                    UNIQUE(subject_id, terminal_epoch)
                )
                """
            )

    def commit(self, pipeline_input: ComposedPipelineInput) -> DurableCommitResult:
        """Re-evaluate the composed closure, then commit only an ACCEPT-ready input."""
        from .pipeline import evaluate_composed_pipeline

        evaluated = evaluate_composed_pipeline(pipeline_input)
        prior = tuple(
            item for item in evaluated.observations
            if item.node_id != "atomic_commit"
        )
        if any(item.decision is ValidationDecision.BLOCK for item in prior):
            return DurableCommitResult(
                DurableCommitDecision.BLOCK,
                ("durable_boundary_prerequisite_blocked",),
            )
        if any(item.decision is ValidationDecision.STALE for item in prior):
            return DurableCommitResult(
                DurableCommitDecision.STALE,
                ("durable_boundary_prerequisite_stale",),
            )
        if any(item.decision is not ValidationDecision.ACCEPT for item in prior):
            return DurableCommitResult(
                DurableCommitDecision.BLOCK,
                ("durable_boundary_closure_incomplete",),
            )

        return self._commit_prevalidated(
            pipeline_input.snapshot,
            pipeline_input.commit_token,
            pipeline_input.commit_state,
            terminal_commit_id=pipeline_input.terminal_commit_id,
        )

    def _commit_prevalidated(
        self,
        snapshot: AcceptanceSnapshot,
        token: CommitToken,
        current: CommitState,
        *,
        terminal_commit_id: str,
    ) -> DurableCommitResult:
        """SQL storage primitive. Production callers should use ``commit``."""
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
                """
                SELECT terminal_commit_id
                FROM terminal_commits
                WHERE subject_id = ? AND terminal_epoch = ?
                """,
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

            conn.execute(
                """
                INSERT INTO terminal_commits (
                    terminal_commit_id,
                    acceptance_snapshot_id,
                    subject_id,
                    terminal_epoch,
                    token_id,
                    subject_state_id,
                    policy_bundle_id,
                    policy_bundle_root,
                    obligation_root,
                    evidence_root,
                    ledger_head,
                    state_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
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
                SELECT
                    terminal_commit_id,
                    acceptance_snapshot_id,
                    subject_id,
                    terminal_epoch,
                    token_id,
                    subject_state_id,
                    policy_bundle_id,
                    policy_bundle_root,
                    obligation_root,
                    evidence_root,
                    ledger_head,
                    state_version
                FROM terminal_commits
                WHERE terminal_commit_id = ?
                """,
                (terminal_commit_id,),
            ).fetchone()
        return None if row is None else DurableTerminalRecord(*row)

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM terminal_commits").fetchone()[0])

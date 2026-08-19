from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
import sqlite3

from .retry import (
    RetryDecision,
    RetryDomain,
    RetryEvent,
    RetryEventKind,
    RetryPolicy,
    RetryResult,
    evaluate_retry_domain,
)


class RetryLedgerDecision(StrEnum):
    WRITTEN = "WRITTEN"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class RetryLedgerResult:
    decision: RetryLedgerDecision
    reasons: tuple[str, ...] = ()
    retry_result: RetryResult | None = None


def _frame(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(8, "big") + raw


def retry_policy_digest(policy: RetryPolicy) -> str:
    payload = b"".join(
        (
            _frame(policy.retry_policy_id),
            _frame(str(policy.max_execution_attempts)),
            _frame(str(policy.max_cumulative_cost)),
            _frame("\n".join(sorted(policy.authorized_retry_reasons))),
            _frame("\n".join(sorted(policy.authorized_recovery_reasons))),
        )
    )
    return hashlib.sha256(b"oma:retry-policy:v1\0" + payload).hexdigest()


def ensure_retry_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS retry_domains (
            retry_domain_id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            pair_id TEXT NOT NULL,
            lineage_id TEXT NOT NULL,
            retry_policy_id TEXT NOT NULL,
            policy_digest TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS retry_events (
            retry_domain_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            event_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
            run_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            pair_id TEXT NOT NULL,
            lineage_id TEXT NOT NULL,
            retry_policy_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            cost_units INTEGER NOT NULL CHECK (cost_units >= 0),
            PRIMARY KEY (retry_domain_id, sequence),
            FOREIGN KEY (retry_domain_id) REFERENCES retry_domains(retry_domain_id)
        )
        """
    )


def _event_from_row(row: tuple[object, ...]) -> RetryEvent:
    return RetryEvent(
        event_id=str(row[0]),
        sequence=int(row[1]),
        kind=RetryEventKind(str(row[2])),
        attempt_number=int(row[3]),
        run_id=str(row[4]),
        subject_id=str(row[5]),
        pair_id=str(row[6]),
        lineage_id=str(row[7]),
        retry_domain_id=str(row[8]),
        retry_policy_id=str(row[9]),
        reason=str(row[10]),
        cost_units=int(row[11]),
    )


def load_retry_events_from_connection(
    conn: sqlite3.Connection,
    domain: RetryDomain,
    policy: RetryPolicy,
) -> tuple[RetryEvent, ...] | None:
    ensure_retry_schema(conn)
    row = conn.execute(
        """
        SELECT subject_id, pair_id, lineage_id, retry_policy_id, policy_digest
        FROM retry_domains WHERE retry_domain_id = ?
        """,
        (domain.retry_domain_id,),
    ).fetchone()
    if row is None:
        return None
    expected = (
        domain.subject_id,
        domain.pair_id,
        domain.lineage_id,
        domain.retry_policy_id,
        retry_policy_digest(policy),
    )
    if tuple(row) != expected:
        return None
    rows = conn.execute(
        """
        SELECT event_id, sequence, kind, attempt_number, run_id, subject_id,
               pair_id, lineage_id, retry_domain_id, retry_policy_id, reason,
               cost_units
        FROM retry_events
        WHERE retry_domain_id = ?
        ORDER BY sequence
        """,
        (domain.retry_domain_id,),
    ).fetchall()
    return tuple(_event_from_row(tuple(row)) for row in rows)


class SQLiteRetryLedger:
    """Append-only factual retry/cost history stored in SQLite.

    The ledger is not an authorization service. It preserves the complete
    observed causal history so acceptance cannot be reopened by omitting older
    retry/cost events at terminalization time.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as conn:
            ensure_retry_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(
        self,
        policy: RetryPolicy,
        domain: RetryDomain,
        initial_event: RetryEvent,
    ) -> RetryLedgerResult:
        initial = evaluate_retry_domain(policy, domain, (initial_event,))
        if (
            initial_event.kind is not RetryEventKind.INITIAL
            or initial_event.sequence != 1
            or initial.decision is not RetryDecision.ALLOW
        ):
            return RetryLedgerResult(
                RetryLedgerDecision.BLOCK,
                ("invalid_retry_ledger_initial_event",),
                initial,
            )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM retry_domains WHERE retry_domain_id = ?",
                (domain.retry_domain_id,),
            ).fetchone() is not None:
                conn.rollback()
                return RetryLedgerResult(
                    RetryLedgerDecision.CONFLICT,
                    ("retry_domain_already_initialized",),
                )
            conn.execute(
                """
                INSERT INTO retry_domains (
                    retry_domain_id, subject_id, pair_id, lineage_id,
                    retry_policy_id, policy_digest
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    domain.retry_domain_id,
                    domain.subject_id,
                    domain.pair_id,
                    domain.lineage_id,
                    domain.retry_policy_id,
                    retry_policy_digest(policy),
                ),
            )
            self._insert_event(conn, initial_event)
            conn.commit()
            return RetryLedgerResult(RetryLedgerDecision.WRITTEN, (), initial)
        except sqlite3.IntegrityError:
            conn.rollback()
            return RetryLedgerResult(
                RetryLedgerDecision.CONFLICT,
                ("retry_ledger_integrity_conflict",),
            )
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return RetryLedgerResult(
                RetryLedgerDecision.BLOCK,
                (f"sqlite_retry_ledger_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def append(
        self,
        policy: RetryPolicy,
        domain: RetryDomain,
        event: RetryEvent,
    ) -> RetryLedgerResult:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = load_retry_events_from_connection(conn, domain, policy)
            if existing is None or not existing:
                conn.rollback()
                return RetryLedgerResult(
                    RetryLedgerDecision.BLOCK,
                    ("retry_domain_not_authoritative",),
                )
            expected_sequence = len(existing) + 1
            if event.sequence != expected_sequence:
                conn.rollback()
                return RetryLedgerResult(
                    RetryLedgerDecision.BLOCK,
                    ("retry_ledger_sequence_mismatch",),
                )
            if (
                event.retry_domain_id != domain.retry_domain_id
                or event.retry_policy_id != domain.retry_policy_id
                or event.subject_id != domain.subject_id
                or event.pair_id != domain.pair_id
                or event.lineage_id != domain.lineage_id
                or not event.event_id
                or not event.run_id
                or event.cost_units < 0
            ):
                conn.rollback()
                return RetryLedgerResult(
                    RetryLedgerDecision.BLOCK,
                    ("retry_ledger_binding_mismatch",),
                )
            self._insert_event(conn, event)
            candidate = existing + (event,)
            result = evaluate_retry_domain(policy, domain, candidate)
            conn.commit()
            return RetryLedgerResult(
                RetryLedgerDecision.WRITTEN
                if result.decision is RetryDecision.ALLOW
                else RetryLedgerDecision.BLOCKED,
                result.reasons,
                result,
            )
        except sqlite3.IntegrityError:
            conn.rollback()
            return RetryLedgerResult(
                RetryLedgerDecision.CONFLICT,
                ("retry_ledger_integrity_conflict",),
            )
        except sqlite3.DatabaseError as exc:
            conn.rollback()
            return RetryLedgerResult(
                RetryLedgerDecision.BLOCK,
                (f"sqlite_retry_ledger_error:{type(exc).__name__}",),
            )
        finally:
            conn.close()

    def get(self, policy: RetryPolicy, domain: RetryDomain) -> tuple[RetryEvent, ...] | None:
        with self._connect() as conn:
            return load_retry_events_from_connection(conn, domain, policy)

    def _insert_event(self, conn: sqlite3.Connection, event: RetryEvent) -> None:
        conn.execute(
            """
            INSERT INTO retry_events (
                retry_domain_id, sequence, event_id, kind, attempt_number,
                run_id, subject_id, pair_id, lineage_id, retry_policy_id,
                reason, cost_units
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.retry_domain_id,
                event.sequence,
                event.event_id,
                event.kind.value,
                event.attempt_number,
                event.run_id,
                event.subject_id,
                event.pair_id,
                event.lineage_id,
                event.retry_policy_id,
                event.reason,
                event.cost_units,
            ),
        )

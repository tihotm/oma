from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import os
from pathlib import Path
import runpy
import subprocess
import sys

from oma.commit import AcceptanceSnapshot, CommitState, CommitToken
from oma.sqlite_commit import DurableCommitDecision, SQLiteTerminalStore, SubjectStateDecision


_pipeline_policy = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _pipeline_policy["policy_enabled_input"]


def fixture():
    snapshot = AcceptanceSnapshot(
        acceptance_snapshot_id="snapshot-1",
        subject_id="subject-1",
        subject_state_id="state-1",
        policy_bundle_id="policy-1",
        obligation_root="obligation-root-1",
        evidence_root="evidence-root-1",
        ledger_head="ledger-1",
        state_version=1,
        terminal_epoch=1,
        policy_bundle_root="policy-root-1",
    )
    token = CommitToken(
        token_id="token-1",
        acceptance_snapshot_id="snapshot-1",
        subject_id="subject-1",
        terminal_epoch=1,
    )
    current = CommitState(
        subject_id="subject-1",
        subject_state_id="state-1",
        policy_bundle_id="policy-1",
        obligation_root="obligation-root-1",
        evidence_root="evidence-root-1",
        ledger_head="ledger-1",
        state_version=1,
        terminal_epoch=1,
        policy_bundle_root="policy-root-1",
    )
    return snapshot, token, current


def test_public_commit_revalidates_full_composed_closure(tmp_path):
    item = policy_enabled_input()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    assert store.initialize_subject_state(item.commit_state).decision is SubjectStateDecision.WRITTEN
    assert store.commit(item).decision is DurableCommitDecision.COMMITTED
    assert store.count() == 1


def test_public_commit_blocks_incomplete_closure(tmp_path):
    item = replace(policy_enabled_input(), aggregation_policy=None)
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    assert store.initialize_subject_state(item.commit_state).decision is SubjectStateDecision.WRITTEN
    result = store.commit(item)
    assert result.decision is DurableCommitDecision.BLOCK
    assert result.reasons == ("durable_boundary_closure_incomplete",)
    assert store.count() == 0


def test_commit_persists_across_reopen(tmp_path):
    snapshot, token, current = fixture()
    path = tmp_path / "oma.db"
    result = SQLiteTerminalStore(path)._commit_prevalidated(snapshot, token, current, terminal_commit_id="terminal-1")
    assert result.decision is DurableCommitDecision.COMMITTED

    reopened = SQLiteTerminalStore(path)
    record = reopened.get("terminal-1")
    assert record is not None
    assert record.acceptance_snapshot_id == "snapshot-1"
    assert record.token_id == "token-1"
    assert reopened.count() == 1


def test_same_subject_epoch_competing_commit_conflicts(tmp_path):
    snapshot, token, current = fixture()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    assert store._commit_prevalidated(snapshot, token, current, terminal_commit_id="terminal-1").decision is DurableCommitDecision.COMMITTED
    competing = replace(token, token_id="token-2")
    result = store._commit_prevalidated(snapshot, competing, current, terminal_commit_id="terminal-2")
    assert result.decision is DurableCommitDecision.CONFLICT
    assert result.reasons == ("terminal_epoch_already_committed",)
    assert store.count() == 1


def test_concurrent_same_subject_epoch_has_one_winner(tmp_path):
    snapshot, token, current = fixture()
    path = tmp_path / "oma.db"
    SQLiteTerminalStore(path)

    def attempt(index: int):
        local_store = SQLiteTerminalStore(path)
        local_token = replace(token, token_id=f"token-{index}")
        return local_store._commit_prevalidated(
            snapshot,
            local_token,
            current,
            terminal_commit_id=f"terminal-{index}",
        ).decision

    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions = list(pool.map(attempt, (1, 2)))

    assert decisions.count(DurableCommitDecision.COMMITTED) == 1
    assert decisions.count(DurableCommitDecision.CONFLICT) == 1
    assert SQLiteTerminalStore(path).count() == 1


def test_token_replay_across_different_subject_conflicts(tmp_path):
    snapshot, token, current = fixture()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    assert store._commit_prevalidated(snapshot, token, current, terminal_commit_id="terminal-1").decision is DurableCommitDecision.COMMITTED

    other_snapshot = replace(
        snapshot,
        acceptance_snapshot_id="snapshot-2",
        subject_id="subject-2",
    )
    replay = replace(
        token,
        acceptance_snapshot_id="snapshot-2",
        subject_id="subject-2",
    )
    other_current = replace(current, subject_id="subject-2")
    result = store._commit_prevalidated(other_snapshot, replay, other_current, terminal_commit_id="terminal-2")
    assert result.decision is DurableCommitDecision.CONFLICT
    assert result.reasons == ("commit_token_replay",)


def test_stale_state_does_not_write(tmp_path):
    snapshot, token, current = fixture()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    result = store._commit_prevalidated(
        snapshot,
        token,
        replace(current, state_version=2),
        terminal_commit_id="terminal-1",
    )
    assert result.decision is DurableCommitDecision.STALE
    assert store.count() == 0


def test_invalid_token_binding_does_not_write(tmp_path):
    snapshot, token, current = fixture()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    result = store._commit_prevalidated(
        snapshot,
        replace(token, subject_id="other"),
        current,
        terminal_commit_id="terminal-1",
    )
    assert result.decision is DurableCommitDecision.BLOCK
    assert store.count() == 0


def test_policy_root_is_persisted(tmp_path):
    snapshot, token, current = fixture()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    store._commit_prevalidated(snapshot, token, current, terminal_commit_id="terminal-1")
    assert store.get("terminal-1").policy_bundle_root == "policy-root-1"


def test_uncommitted_process_exit_rolls_back(tmp_path):
    path = tmp_path / "oma.db"
    SQLiteTerminalStore(path)
    script = r'''
import os, sqlite3, sys
path = sys.argv[1]
conn = sqlite3.connect(path, isolation_level=None)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=FULL")
conn.execute("BEGIN IMMEDIATE")
conn.execute("""INSERT INTO terminal_commits(
 terminal_commit_id,acceptance_snapshot_id,subject_id,terminal_epoch,token_id,
 subject_state_id,policy_bundle_id,policy_bundle_root,obligation_root,evidence_root,ledger_head,state_version
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",(
 "terminal-crash","snapshot-crash","subject-crash",9,"token-crash",
 "state","policy","policy-root","obligation","evidence","ledger",1
))
os._exit(23)
'''
    result = subprocess.run([sys.executable, "-c", script, str(path)])
    assert result.returncode == 23
    assert SQLiteTerminalStore(path).count() == 0


def test_committed_process_exit_survives_reopen(tmp_path):
    path = tmp_path / "oma.db"
    script = r'''
import os, sys
from oma.commit import AcceptanceSnapshot, CommitState, CommitToken
from oma.sqlite_commit import SQLiteTerminalStore
path = sys.argv[1]
s = AcceptanceSnapshot("snap","subject","state","policy","obligation","evidence","ledger",1,1,"policy-root")
t = CommitToken("token","snap","subject",1)
c = CommitState("subject","state","policy","obligation","evidence","ledger",1,1,policy_bundle_root="policy-root")
r = SQLiteTerminalStore(path)._commit_prevalidated(s,t,c,terminal_commit_id="terminal")
assert r.decision.value == "COMMITTED"
os._exit(0)
'''
    env = os.environ.copy()
    result = subprocess.run([sys.executable, "-c", script, str(path)], env=env)
    assert result.returncode == 0
    reopened = SQLiteTerminalStore(path)
    assert reopened.count() == 1
    assert reopened.get("terminal").token_id == "token"

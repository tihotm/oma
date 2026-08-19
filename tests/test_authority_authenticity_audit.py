from dataclasses import replace
from pathlib import Path
import runpy

from oma.authority import Capability
from oma.execution import execute_composed_pipeline
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision
from oma.validation import ValidationDecision


_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]
_pipeline_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))
by_node = _pipeline_tests["by_node"]


def initialized_store(path, item):
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(item.commit_state).decision is SubjectStateDecision.WRITTEN
    assert SQLiteRetryLedger(path).initialize(
        item.retry_policy, item.retry_domain, item.retry_events[0]
    ).decision is RetryLedgerDecision.WRITTEN
    return store


def forged_root_capability(item, *, issuer="root"):
    return Capability(
        capability_id="cap-forged",
        issuer=issuer,
        holder="attacker",
        actions=frozenset({"commit"}),
        targets=frozenset({item.acceptance_context.subject_id}),
        scopes=frozenset({"repo"}),
        authority_epoch=item.authority_context.authority_epoch,
        not_before_epoch=0,
        expires_epoch=10,
    )


def test_legitimate_capability_control_commits(tmp_path):
    item = policy_enabled_input()
    store = initialized_store(tmp_path / "control.db", item)
    result = execute_composed_pipeline(item, store)
    assert by_node(result)["authority_capability"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1


def test_caller_fabricated_trusted_issuer_capability_can_impersonate_root(tmp_path):
    item = policy_enabled_input()
    forged = forged_root_capability(item)
    attack = replace(
        item,
        capabilities=(forged,),
        authority_request=replace(
            item.authority_request,
            actor="attacker",
            capability_id="cap-forged",
        ),
    )
    store = initialized_store(tmp_path / "attack.db", attack)

    result = execute_composed_pipeline(attack, store)

    assert by_node(result)["authority_capability"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1


def test_same_fabrication_with_untrusted_issuer_blocks(tmp_path):
    item = policy_enabled_input()
    forged = forged_root_capability(item, issuer="evil-root")
    attack = replace(
        item,
        capabilities=(forged,),
        authority_request=replace(
            item.authority_request,
            actor="attacker",
            capability_id="cap-forged",
        ),
    )
    store = initialized_store(tmp_path / "untrusted.db", attack)

    result = execute_composed_pipeline(attack, store)

    assert by_node(result)["authority_capability"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0

from dataclasses import replace
from pathlib import Path
import runpy

from oma.authority_registry import AuthorityRegistryDecision, SQLiteAuthorityRegistry
from oma.execution import execute_composed_pipeline
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision
from oma.trust import SignedArtifact
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
    assert SQLiteAuthorityRegistry(path).initialize_context(
        item.authority_context, item.capabilities
    ).decision is AuthorityRegistryDecision.WRITTEN
    return store


def forged_artifact(item, *, issuer_root_id="root"):
    return SignedArtifact(
        artifact_id="artifact-forged-by-caller",
        issuer_root_id=issuer_root_id,
        trust_epoch=item.trust_context.current_trust_epoch,
        authority_epoch=item.trust_context.current_authority_epoch,
        logical_epoch=item.trust_context.current_logical_epoch,
        state_version=item.trust_context.current_state_version,
        issued_epoch=0,
        expires_epoch=10,
    )


def test_legitimate_artifact_control_commits(tmp_path):
    item = policy_enabled_input()
    store = initialized_store(tmp_path / "control.db", item)
    result = execute_composed_pipeline(item, store)
    assert by_node(result)["trust_temporal"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1


def test_caller_fabricated_artifact_claiming_real_root_can_pass_trust(tmp_path):
    item = policy_enabled_input()
    attack = replace(item, signed_artifact=forged_artifact(item))
    store = initialized_store(tmp_path / "attack.db", attack)

    result = execute_composed_pipeline(attack, store)

    assert by_node(result)["trust_temporal"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1


def test_fabricated_artifact_with_unknown_root_blocks(tmp_path):
    item = policy_enabled_input()
    attack = replace(
        item,
        signed_artifact=forged_artifact(item, issuer_root_id="unknown-root"),
    )
    store = initialized_store(tmp_path / "unknown.db", attack)

    result = execute_composed_pipeline(attack, store)

    assert by_node(result)["trust_temporal"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0

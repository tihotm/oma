from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.pipeline import evaluate_composed_pipeline
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision
from oma.terminal import canonical_terminal_policy, evaluate_terminal_barrier
from oma.validation import (
    ValidationDecision,
    canonical_validation_graph,
    validation_closure_digest,
    validation_observation_digest,
)


_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]


def by_node(result):
    return {item.node_id: item for item in result.observations}


def initialized_store(path, item):
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(item.commit_state).decision is SubjectStateDecision.WRITTEN
    return store


def test_pipeline_terminal_observation_uses_real_barrier_root():
    item = policy_enabled_input()
    result = evaluate_composed_pipeline(item)
    terminal_index = next(
        index for index, observation in enumerate(result.observations)
        if observation.node_id == "terminal_barrier"
    )
    prerequisites = result.observations[:terminal_index]
    expected = evaluate_terminal_barrier(
        canonical_terminal_policy(item.termination_policy_id),
        prerequisites,
        requested_action=item.terminal_action,
    )
    assert expected.decision.value == "ALLOW"
    assert expected.terminal_barrier_root is not None
    assert result.observations[terminal_index].evidence_root == expected.terminal_barrier_root


def test_validation_closure_digest_is_deterministic_and_graph_bound():
    item = policy_enabled_input()
    result = evaluate_composed_pipeline(item)
    graph = canonical_validation_graph()
    digest = validation_closure_digest(graph, result.observations)
    assert digest == result.result.validation_closure_digest
    assert digest is not None

    other_graph = replace(graph, validation_graph_id="oma:canonical-validation:other")
    assert validation_closure_digest(other_graph, result.observations) != digest


def test_fact_change_that_stays_valid_changes_terminal_and_closure_roots():
    item = policy_enabled_input()
    first = evaluate_composed_pipeline(item)
    changed = replace(
        item,
        signed_artifact=replace(item.signed_artifact, artifact_id="artifact-2"),
    )
    second = evaluate_composed_pipeline(changed)

    assert first.result.decision is ValidationDecision.NOT_DONE
    assert second.result.decision is ValidationDecision.NOT_DONE
    assert by_node(first)["trust_temporal"].decision is ValidationDecision.ACCEPT
    assert by_node(second)["trust_temporal"].decision is ValidationDecision.ACCEPT
    assert by_node(first)["trust_temporal"].evidence_root != by_node(second)["trust_temporal"].evidence_root
    assert by_node(first)["terminal_barrier"].evidence_root != by_node(second)["terminal_barrier"].evidence_root
    assert first.result.validation_closure_digest != second.result.validation_closure_digest


def test_durable_record_persists_exact_precommit_proof(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    store = initialized_store(path, item)

    evaluated = evaluate_composed_pipeline(item)
    prior = tuple(
        observation for observation in evaluated.observations
        if observation.node_id != "atomic_commit"
    )
    graph = canonical_validation_graph()
    expected_digest = validation_observation_digest(
        graph,
        prior,
        domain="precommit",
    )
    expected_terminal_root = by_node(evaluated)["terminal_barrier"].evidence_root

    executed = execute_composed_pipeline(item, store)
    assert executed.result.decision is ValidationDecision.ACCEPT

    record = store.get(item.terminal_commit_id)
    assert record is not None
    assert record.validation_graph_id == graph.validation_graph_id
    assert record.terminal_barrier_root == expected_terminal_root
    assert record.precommit_closure_digest == expected_digest
    assert record.precommit_closure_digest is not None

    reopened = SQLiteTerminalStore(path)
    persisted = reopened.get(item.terminal_commit_id)
    assert persisted is not None
    assert persisted.validation_graph_id == record.validation_graph_id
    assert persisted.terminal_barrier_root == record.terminal_barrier_root
    assert persisted.precommit_closure_digest == record.precommit_closure_digest


def test_durable_precommit_proof_changes_with_valid_factual_input(tmp_path):
    first_item = policy_enabled_input()
    first_store = initialized_store(tmp_path / "first.db", first_item)
    first = execute_composed_pipeline(first_item, first_store)
    assert first.result.decision is ValidationDecision.ACCEPT
    first_record = first_store.get(first_item.terminal_commit_id)
    assert first_record is not None

    second_item = replace(
        policy_enabled_input(),
        signed_artifact=replace(policy_enabled_input().signed_artifact, artifact_id="artifact-2"),
    )
    second_store = initialized_store(tmp_path / "second.db", second_item)
    second = execute_composed_pipeline(second_item, second_store)
    assert second.result.decision is ValidationDecision.ACCEPT
    second_record = second_store.get(second_item.terminal_commit_id)
    assert second_record is not None

    assert first_record.precommit_closure_digest != second_record.precommit_closure_digest
    assert first_record.terminal_barrier_root != second_record.terminal_barrier_root

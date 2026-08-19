from oma import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def context() -> AcceptanceContext:
    return AcceptanceContext(
        subject_id="subject:1",
        subject_state_id="state:abc",
        verification_context_id="verify:v1",
        policy_bundle_id="policy:v1",
        required_obligations=frozenset({"tests", "scope"}),
    )


def evidence(obligation: str, *, evidence_id: str | None = None, passed: bool = True, **overrides) -> Evidence:
    values = dict(
        evidence_id=evidence_id or f"evidence:{obligation}",
        obligation_id=obligation,
        subject_id="subject:1",
        subject_state_id="state:abc",
        verification_context_id="verify:v1",
        policy_bundle_id="policy:v1",
        passed=passed,
    )
    values.update(overrides)
    return Evidence(**values)


def test_accepts_complete_correctly_bound_pass_set():
    result = evaluate_acceptance(context(), [evidence("tests"), evidence("scope")])
    assert result.decision is AcceptanceDecision.ACCEPT


def test_empty_set_is_not_done():
    assert evaluate_acceptance(context(), []).decision is AcceptanceDecision.NOT_DONE


def test_missing_required_obligation_is_not_done():
    assert evaluate_acceptance(context(), [evidence("tests")]).decision is AcceptanceDecision.NOT_DONE


def test_failed_required_obligation_is_not_done():
    result = evaluate_acceptance(context(), [evidence("tests", passed=False), evidence("scope")])
    assert result.decision is AcceptanceDecision.NOT_DONE


def test_wrong_subject_blocks():
    result = evaluate_acceptance(context(), [evidence("tests", subject_id="subject:2")])
    assert result.decision is AcceptanceDecision.BLOCK


def test_wrong_subject_state_blocks():
    result = evaluate_acceptance(context(), [evidence("tests", subject_state_id="state:old")])
    assert result.decision is AcceptanceDecision.BLOCK


def test_wrong_verification_context_blocks():
    result = evaluate_acceptance(context(), [evidence("tests", verification_context_id="verify:v0")])
    assert result.decision is AcceptanceDecision.BLOCK


def test_wrong_policy_bundle_blocks():
    result = evaluate_acceptance(context(), [evidence("tests", policy_bundle_id="policy:v0")])
    assert result.decision is AcceptanceDecision.BLOCK


def test_unknown_obligation_blocks():
    result = evaluate_acceptance(context(), [evidence("hidden")])
    assert result.decision is AcceptanceDecision.BLOCK


def test_duplicate_evidence_id_blocks():
    result = evaluate_acceptance(
        context(),
        [evidence("tests", evidence_id="same"), evidence("scope", evidence_id="same")],
    )
    assert result.decision is AcceptanceDecision.BLOCK


def test_multiple_evidence_for_same_obligation_blocks_best_of_n():
    result = evaluate_acceptance(
        context(),
        [evidence("tests", evidence_id="a", passed=False), evidence("tests", evidence_id="b", passed=True)],
    )
    assert result.decision is AcceptanceDecision.BLOCK


def test_integrity_failure_precedes_missing_obligation():
    result = evaluate_acceptance(context(), [evidence("tests", subject_state_id="state:old")])
    assert result.decision is AcceptanceDecision.BLOCK


def test_integrity_failure_precedes_failed_obligation():
    result = evaluate_acceptance(
        context(),
        [evidence("tests", passed=False, policy_bundle_id="policy:v0"), evidence("scope")],
    )
    assert result.decision is AcceptanceDecision.BLOCK


def test_false_done_is_prevented_when_obligation_failed():
    result = evaluate_acceptance(context(), [evidence("tests"), evidence("scope", passed=False)])
    assert result.decision is not AcceptanceDecision.ACCEPT

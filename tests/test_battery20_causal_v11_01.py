from oma.acceptance import AcceptanceContext, AcceptanceDecision, evaluate_acceptance


def test_v11_01_empty_acceptance_denominator_currently_accepts():
    context = AcceptanceContext(
        subject_id="subject:1",
        subject_state_id="state:1",
        verification_context_id="verify:1",
        policy_bundle_id="bundle:1",
        required_obligations=frozenset(),
    )
    assert evaluate_acceptance(context, ()).decision is AcceptanceDecision.ACCEPT

from oma.obligation import ObligationDecision, ObligationManifest, ObligationSpec, evaluate_obligation_manifest


def evaluate(obligation_id, requirement_digest):
    manifest = ObligationManifest("set:1", (ObligationSpec(obligation_id, requirement_digest, 1),))
    return evaluate_obligation_manifest(
        manifest,
        manifest,
        acceptance_required_obligations=frozenset({obligation_id}),
    )


def test_v12_19_valid_obligation_inputs_can_collide_across_id_digest_boundary():
    left = evaluate("a", "b\0c")
    right = evaluate("a\0b", "c")
    assert left.decision is ObligationDecision.ALLOW
    assert right.decision is ObligationDecision.ALLOW
    assert left.obligation_root == right.obligation_root

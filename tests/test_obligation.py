from oma.obligation import (
    ObligationDecision,
    ObligationManifest,
    ObligationSpec,
    evaluate_obligation_manifest,
    obligation_root,
)


def manifest(*items, set_id="set-1"):
    return ObligationManifest(
        set_id,
        tuple(ObligationSpec(*item) for item in items),
    )


BASE = manifest(("tests", "digest:t", 2), ("scope", "digest:s", 1))


def test_exact_manifest_allows():
    result = evaluate_obligation_manifest(
        BASE,
        BASE,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    )
    assert result.decision is ObligationDecision.ALLOW
    assert result.obligation_root


def test_root_deterministic_across_order():
    other = manifest(("scope", "digest:s", 1), ("tests", "digest:t", 2))
    assert obligation_root(BASE) == obligation_root(other)


def test_removal_blocks():
    result = evaluate_obligation_manifest(
        BASE,
        manifest(("tests", "digest:t", 2)),
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    )
    assert result.decision is ObligationDecision.BLOCK


def test_substitution_blocks():
    result = evaluate_obligation_manifest(
        BASE,
        manifest(("tests", "evil", 2), ("scope", "digest:s", 1)),
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    )
    assert "obligation_substitution:tests" in result.reasons


def test_downgrade_blocks():
    result = evaluate_obligation_manifest(
        BASE,
        manifest(("tests", "digest:t", 1), ("scope", "digest:s", 1)),
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    )
    assert "obligation_downgrade:tests" in result.reasons


def test_upgrade_mutation_blocks_without_new_set():
    result = evaluate_obligation_manifest(
        BASE,
        manifest(("tests", "digest:t", 3), ("scope", "digest:s", 1)),
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    )
    assert "obligation_mutation:tests" in result.reasons


def test_added_obligation_blocks_without_new_set():
    presented = manifest(
        ("tests", "digest:t", 2),
        ("scope", "digest:s", 1),
        ("extra", "digest:e", 1),
    )
    assert evaluate_obligation_manifest(
        BASE,
        presented,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    ).decision is ObligationDecision.BLOCK


def test_set_id_mismatch_blocks():
    presented = ObligationManifest("set-2", BASE.obligations)
    assert evaluate_obligation_manifest(
        BASE,
        presented,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    ).decision is ObligationDecision.BLOCK


def test_acceptance_denominator_reduction_blocks():
    result = evaluate_obligation_manifest(
        BASE,
        BASE,
        acceptance_required_obligations=frozenset({"tests"}),
    )
    assert "acceptance_denominator_missing:scope" in result.reasons


def test_acceptance_denominator_extra_blocks():
    result = evaluate_obligation_manifest(
        BASE,
        BASE,
        acceptance_required_obligations=frozenset({"tests", "scope", "fake"}),
    )
    assert "acceptance_denominator_unknown:fake" in result.reasons


def test_duplicate_id_blocks():
    presented = manifest(("tests", "digest:t", 2), ("tests", "digest:t", 2))
    assert evaluate_obligation_manifest(
        BASE,
        presented,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    ).decision is ObligationDecision.BLOCK


def test_empty_set_id_blocks():
    presented = ObligationManifest("", BASE.obligations)
    assert evaluate_obligation_manifest(
        BASE,
        presented,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    ).decision is ObligationDecision.BLOCK


def test_empty_obligations_blocks():
    presented = ObligationManifest("set-1", ())
    assert evaluate_obligation_manifest(
        BASE,
        presented,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    ).decision is ObligationDecision.BLOCK


def test_invalid_digest_blocks():
    presented = manifest(("tests", "", 2), ("scope", "digest:s", 1))
    assert evaluate_obligation_manifest(
        BASE,
        presented,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    ).decision is ObligationDecision.BLOCK


def test_invalid_strength_blocks():
    presented = manifest(("tests", "digest:t", 0), ("scope", "digest:s", 1))
    assert evaluate_obligation_manifest(
        BASE,
        presented,
        acceptance_required_obligations=frozenset({"tests", "scope"}),
    ).decision is ObligationDecision.BLOCK

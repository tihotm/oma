from dataclasses import replace

from oma.policy import (
    PolicyBinding,
    PolicyBundle,
    PolicyBundleDecision,
    evaluate_policy_bundle,
    policy_bundle_root,
    policy_object_root,
)


KINDS = frozenset(
    {
        "identity",
        "scope",
        "authority",
        "trust",
        "obligation",
        "provenance",
        "aggregation",
        "retry",
        "termination",
    }
)


def bundle():
    return PolicyBundle(
        "bundle-1",
        3,
        tuple(
            PolicyBinding(kind, f"{kind}:v1", f"root:{kind}")
            for kind in sorted(KINDS)
        ),
    )


def evaluate(expected=None, presented=None, bound=("bundle-1",)):
    expected = expected or bundle()
    presented = presented or expected
    return evaluate_policy_bundle(
        expected,
        presented,
        required_policy_kinds=KINDS,
        bound_policy_bundle_ids=bound,
    )


def test_valid_allows():
    assert evaluate().decision is PolicyBundleDecision.ALLOW


def test_root_is_deterministic():
    assert policy_bundle_root(bundle()) == policy_bundle_root(bundle())


def test_binding_order_is_irrelevant():
    item = bundle()
    reordered = replace(item, bindings=tuple(reversed(item.bindings)))
    assert policy_bundle_root(item) == policy_bundle_root(reordered)


def test_bundle_id_mismatch_blocks():
    assert evaluate(presented=replace(bundle(), policy_bundle_id="x")).decision is PolicyBundleDecision.BLOCK


def test_bundle_epoch_mismatch_blocks():
    assert evaluate(presented=replace(bundle(), bundle_epoch=4)).decision is PolicyBundleDecision.BLOCK


def test_missing_policy_kind_blocks():
    item = bundle()
    assert evaluate(presented=replace(item, bindings=item.bindings[:-1])).decision is PolicyBundleDecision.BLOCK


def test_extra_policy_kind_blocks():
    item = bundle()
    extra = PolicyBinding("extra", "x", "r")
    assert evaluate(presented=replace(item, bindings=item.bindings + (extra,))).decision is PolicyBundleDecision.BLOCK


def test_duplicate_policy_kind_blocks():
    item = bundle()
    assert evaluate(presented=replace(item, bindings=item.bindings + (item.bindings[0],))).decision is PolicyBundleDecision.BLOCK


def test_policy_id_swap_blocks():
    item = bundle()
    bindings = list(item.bindings)
    bindings[0] = replace(bindings[0], policy_id="evil")
    assert evaluate(presented=replace(item, bindings=tuple(bindings))).decision is PolicyBundleDecision.BLOCK


def test_policy_root_swap_blocks():
    item = bundle()
    bindings = list(item.bindings)
    bindings[0] = replace(bindings[0], policy_root="evil")
    assert evaluate(presented=replace(item, bindings=tuple(bindings))).decision is PolicyBundleDecision.BLOCK


def test_empty_policy_id_blocks():
    item = bundle()
    bindings = list(item.bindings)
    bindings[0] = replace(bindings[0], policy_id="")
    assert evaluate(presented=replace(item, bindings=tuple(bindings))).decision is PolicyBundleDecision.BLOCK


def test_empty_policy_root_blocks():
    item = bundle()
    bindings = list(item.bindings)
    bindings[0] = replace(bindings[0], policy_root="")
    assert evaluate(presented=replace(item, bindings=tuple(bindings))).decision is PolicyBundleDecision.BLOCK


def test_empty_bundle_id_blocks():
    assert evaluate(expected=replace(bundle(), policy_bundle_id="")).decision is PolicyBundleDecision.BLOCK


def test_negative_epoch_blocks():
    assert evaluate(expected=replace(bundle(), bundle_epoch=-1)).decision is PolicyBundleDecision.BLOCK


def test_bound_context_mismatch_blocks():
    assert evaluate(bound=("bundle-1", "other")).decision is PolicyBundleDecision.BLOCK


def test_empty_bound_context_blocks():
    assert evaluate(bound=("bundle-1", "")).decision is PolicyBundleDecision.BLOCK


def test_all_bound_contexts_match_allows():
    assert evaluate(bound=("bundle-1", "bundle-1", "bundle-1")).decision is PolicyBundleDecision.ALLOW


def test_policy_object_root_is_deterministic_for_sets():
    left = {"a": frozenset({"x", "y"}), "n": 1}
    right = {"n": 1, "a": frozenset({"y", "x"})}
    assert policy_object_root("scope", left) == policy_object_root("scope", right)


def test_policy_object_root_has_domain_separation():
    value = {"x": 1}
    assert policy_object_root("scope", value) != policy_object_root("retry", value)

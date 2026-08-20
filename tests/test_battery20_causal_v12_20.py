from oma.obligation import ObligationManifest, ObligationSpec, obligation_root


def test_v12_20_control_free_obligation_digest_change_changes_root():
    left = ObligationManifest("set:1", (ObligationSpec("ob:1", "digest:1", 1),))
    right = ObligationManifest("set:1", (ObligationSpec("ob:1", "digest:2", 1),))
    assert obligation_root(left) != obligation_root(right)

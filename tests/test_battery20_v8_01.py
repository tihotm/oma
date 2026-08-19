from oma.obligation import ObligationManifest, ObligationSpec, obligation_root


def test_distinct_obligation_manifests_can_share_root_via_nul_boundary_shift():
    a=ObligationManifest("set",(ObligationSpec("a","b\x00c",1),))
    b=ObligationManifest("set",(ObligationSpec("a\x00b","c",1),))
    assert a != b
    assert obligation_root(a) == obligation_root(b)

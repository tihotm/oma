from oma.obligation import ObligationManifest, ObligationSpec, obligation_root


def test_obligation_root_is_independent_of_manifest_item_order():
    a=ObligationSpec("a","ra",1); b=ObligationSpec("b","rb",2)
    assert obligation_root(ObligationManifest("set",(a,b))) == obligation_root(ObligationManifest("set",(b,a)))

from dataclasses import replace
from oma.authority import AuthorityContext
from oma.authority_registry import authority_context_digest


def test_authority_context_digest_omits_now_epoch():
    base=AuthorityContext('ctx',1,7,frozenset({'root'}))
    assert authority_context_digest(base) == authority_context_digest(replace(base, now_epoch=700))

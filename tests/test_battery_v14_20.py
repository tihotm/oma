from dataclasses import replace
from oma.authority import AuthorityContext
from oma.authority_registry import authority_context_digest


def test_authority_context_digest_changes_with_authority_epoch():
    base=AuthorityContext('ctx',1,7,frozenset({'root'}))
    assert authority_context_digest(base) != authority_context_digest(replace(base,authority_epoch=2))

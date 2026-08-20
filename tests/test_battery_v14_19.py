from dataclasses import replace
from oma.authority import AuthorityContext
from oma.authority_registry import authority_context_digest


def test_authority_context_digest_changes_with_trusted_issuers():
    base=AuthorityContext('ctx',1,7,frozenset({'root'}))
    changed=replace(base,trusted_issuers=frozenset({'other'}))
    assert authority_context_digest(base) != authority_context_digest(changed)

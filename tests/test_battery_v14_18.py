from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority
from oma.authority_registry import authority_context_digest


def test_same_authority_digest_can_flip_expired_to_allow_by_rewinding_now():
    cap=Capability('cap','root','agent',frozenset({'commit'}),frozenset({'subject'}),frozenset({'repo'}),1,5,10)
    req=AuthorityRequest('agent','commit','subject','repo','cap')
    expired=AuthorityContext('ctx',1,100,frozenset({'root'}))
    rewound=AuthorityContext('ctx',1,7,frozenset({'root'}))
    assert authority_context_digest(expired) == authority_context_digest(rewound)
    assert evaluate_authority(expired,(cap,),req).decision is AuthorityDecision.STALE
    assert evaluate_authority(rewound,(cap,),req).decision is AuthorityDecision.ALLOW

import pytest
from oma.identity import (
    IdentityDecision, IdentityPolicy, StrictSchema,
    canonicalize_identifier, content_digest, identity_digest,
    make_typed_identity, strict_parse_json,
)

POLICY = IdentityPolicy("id:v1")
SCHEMA = StrictSchema("schema:v1", 1, frozenset({"namespace","id"}), frozenset({"version"}))

def test_nfkc_equivalence():
    assert canonicalize_identifier("ＡＢＣ", POLICY) == "abc"

def test_casefold_equivalence():
    assert canonicalize_identifier("Subject:ABC", POLICY) == "subject:abc"

def test_control_character_blocks():
    assert canonicalize_identifier("abc\u0000", POLICY) is None

def test_leading_whitespace_blocks():
    assert canonicalize_identifier(" abc", POLICY) is None

def test_empty_policy_id_blocks_identity():
    result = make_typed_identity("subject", "1", IdentityPolicy(""))
    assert result.decision is IdentityDecision.BLOCK

def test_namespace_is_part_of_identity():
    a = make_typed_identity("subject", "same", POLICY).identity
    b = make_typed_identity("capability", "same", POLICY).identity
    assert a != b
    assert identity_digest(a) != identity_digest(b)

def test_same_namespace_canonical_equivalence_matches():
    a = make_typed_identity("SUBJECT", "ＡBC", POLICY).identity
    b = make_typed_identity("subject", "abc", POLICY).identity
    assert a == b

def test_content_digest_domain_separated_from_identity_digest():
    ident = make_typed_identity("subject","x",POLICY).identity
    assert identity_digest(ident) != content_digest(b"subject\x00x")

def test_duplicate_field_blocks():
    result = strict_parse_json('{"namespace":"subject","id":"1","id":"2"}', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_unknown_field_blocks():
    result = strict_parse_json('{"namespace":"subject","id":"1","extra":1}', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_missing_required_field_blocks():
    result = strict_parse_json('{"namespace":"subject"}', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_trailing_data_blocks():
    result = strict_parse_json('{"namespace":"subject","id":"1"} garbage', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_multiple_documents_blocks():
    result = strict_parse_json('{"namespace":"subject","id":"1"} {"namespace":"x","id":"2"}', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_root_array_blocks():
    result = strict_parse_json('["subject","1"]', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_block(constant):
    result = strict_parse_json(f'{{"namespace":"subject","id":"1","version":{constant}}}', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_integer_beyond_safe_precision_blocks():
    result = strict_parse_json('{"namespace":"subject","id":"1","version":9007199254740992}', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_fractional_number_blocks_as_ambiguous():
    result = strict_parse_json('{"namespace":"subject","id":"1","version":1.5}', SCHEMA)
    assert result.decision is IdentityDecision.BLOCK

def test_integral_float_is_accepted():
    result = strict_parse_json('{"namespace":"subject","id":"1","version":1.0}', SCHEMA)
    assert result.decision is IdentityDecision.ALLOW

def test_null_absent_distinction_preserved_for_optional_field():
    absent = strict_parse_json('{"namespace":"subject","id":"1"}', SCHEMA)
    null = strict_parse_json('{"namespace":"subject","id":"1","version":null}', SCHEMA)
    assert absent.decision is IdentityDecision.ALLOW
    assert null.decision is IdentityDecision.ALLOW
    assert "version" not in absent.value and "version" in null.value

def test_valid_document_allows():
    result = strict_parse_json('{"namespace":"Subject","id":"ＡBC","version":1}', SCHEMA)
    assert result.decision is IdentityDecision.ALLOW

def test_invalid_schema_version_blocks():
    result = strict_parse_json('{"namespace":"subject","id":"1"}', StrictSchema("x",0,frozenset()))
    assert result.decision is IdentityDecision.BLOCK

def test_visual_confusable_not_collapsed():
    latin = canonicalize_identifier("paypal", POLICY)
    cyrillic = canonicalize_identifier("pаypal", POLICY)
    assert latin != cyrillic

def test_namespace_type_confusion_same_raw_id_stays_distinct():
    subject = make_typed_identity("subject","42",POLICY).identity
    policy = make_typed_identity("policy","42",POLICY).identity
    capability = make_typed_identity("capability","42",POLICY).identity
    assert len({identity_digest(subject), identity_digest(policy), identity_digest(capability)}) == 3

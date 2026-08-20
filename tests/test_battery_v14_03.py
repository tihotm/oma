import pytest

from oma.policy import policy_object_root


def test_policy_root_lone_surrogate_raises_encoding_error():
    with pytest.raises(UnicodeEncodeError):
        policy_object_root("probe", {"value": "\ud800"})

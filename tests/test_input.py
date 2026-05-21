import pytest
from checker.input import normalize, ValidationError
from models import ArticleInput


def test_doi_strips_url_prefix():
    result = normalize(doi="https://doi.org/10.1234/test")
    assert result.doi == "10.1234/test"


def test_doi_lowercased():
    result = normalize(doi="10.1234/TEST")
    assert result.doi == "10.1234/test"


def test_issn_valid_format_passes():
    result = normalize(issn="1234-5678")
    assert result.issn == "1234-5678"


def test_issn_invalid_format_raises():
    with pytest.raises(ValidationError, match="ISSN"):
        normalize(issn="12345678")


def test_requires_at_least_one_identifier():
    with pytest.raises(ValidationError, match="at least one"):
        normalize()


def test_title_only_valid():
    result = normalize(title="Some Article Title")
    assert result.title == "Some Article Title"
    assert result.doi is None


def test_all_fields_passed_through():
    result = normalize(
        title="T", doi="10.1/x", issn="0000-0001",
        author="A", journal="J"
    )
    assert result.author == "A"
    assert result.journal == "J"


def test_whitespace_only_doi_treated_as_missing():
    with pytest.raises(ValidationError, match="at least one"):
        normalize(doi="   ")

import re
from models import ArticleInput


class ValidationError(ValueError):
    pass


def normalize(
    title: str | None = None,
    doi: str | None = None,
    issn: str | None = None,
    author: str | None = None,
    journal: str | None = None,
) -> ArticleInput:
    if doi:
        doi = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/").lower()

    if issn:
        if not re.fullmatch(r"\d{4}-\d{3}[\dX]", issn, re.IGNORECASE):
            raise ValidationError(f"ISSN must be in XXXX-XXXX format, got: {issn!r}")
        issn = issn.upper()

    if not any([title, doi, issn]):
        raise ValidationError("at least one of title, doi, or issn is required")

    return ArticleInput(title=title, doi=doi, issn=issn, author=author, journal=journal)

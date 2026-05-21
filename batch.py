import csv
import json
from pathlib import Path
from typing import Generator
from models import ArticleInput, Verdict
from checker.pipeline import check


def parse_file(path: str) -> Generator[ArticleInput, None, None]:
    p = Path(path)
    if p.suffix == ".csv":
        yield from _parse_csv(path)
    elif p.suffix == ".json":
        yield from _parse_json(path)
    else:
        raise ValueError(f"Unsupported file format: {p.suffix}. Use .csv or .json")


def _parse_csv(path: str) -> Generator[ArticleInput, None, None]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield ArticleInput(
                title=row.get("title") or None,
                doi=row.get("doi") or None,
                issn=row.get("issn") or None,
                author=row.get("author") or None,
                journal=row.get("journal") or None,
            )


def _parse_json(path: str) -> Generator[ArticleInput, None, None]:
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    for item in items:
        yield ArticleInput(
            title=item.get("title"),
            doi=item.get("doi"),
            issn=item.get("issn"),
            author=item.get("author"),
            journal=item.get("journal"),
        )


def stream_check(
    articles: list[ArticleInput],
) -> Generator[tuple[ArticleInput, Verdict | None, Exception | None], None, None]:
    for article in articles:
        try:
            verdict = check(article)
            yield (article, verdict, None)
        except Exception as e:
            yield (article, None, e)

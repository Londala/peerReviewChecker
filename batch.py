import csv
import json
import sys
from pathlib import Path
from typing import Generator
from models import ArticleInput, Verdict
from checker.input import normalize, ValidationError
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
        for i, row in enumerate(reader, start=2):  # row 1 is header
            try:
                yield normalize(
                    title=row.get("title") or None,
                    doi=row.get("doi") or None,
                    issn=row.get("issn") or None,
                    author=row.get("author") or None,
                    journal=row.get("journal") or None,
                )
            except ValidationError as e:
                print(f"Skipping CSV row {i}: {e}", file=sys.stderr)


def _parse_json(path: str) -> Generator[ArticleInput, None, None]:
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    for i, item in enumerate(items, start=1):
        try:
            yield normalize(
                title=item.get("title"),
                doi=item.get("doi"),
                issn=item.get("issn"),
                author=item.get("author"),
                journal=item.get("journal"),
            )
        except ValidationError as e:
            print(f"Skipping JSON item {i}: {e}", file=sys.stderr)


def stream_check(
    articles: list[ArticleInput],
) -> Generator[tuple[ArticleInput, Verdict | None, Exception | None], None, None]:
    for article in articles:
        try:
            verdict = check(article)
            yield (article, verdict, None)
        except Exception as e:
            yield (article, None, e)

from models import ArticleInput, Verdict
from checker.sources import crossref, doaj, openalex, sherpa, websearch
from checker.verdict import aggregate

FALLBACK_THRESHOLD = 0.6


def check(article: ArticleInput) -> Verdict:
    results = []

    results.append(crossref.lookup(article))
    results.append(doaj.lookup(article))
    results.append(openalex.lookup(article))

    if article.issn:
        results.append(sherpa.lookup(article))

    best_so_far = max(r.confidence for r in results)
    if best_so_far < FALLBACK_THRESHOLD:
        results.append(websearch.lookup(article))

    return aggregate(results)

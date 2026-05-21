from models import ArticleInput, Verdict
from checker.sources import crossref, doaj, websearch
from checker.verdict import aggregate

FALLBACK_THRESHOLD = 0.6


def check(article: ArticleInput) -> Verdict:
    results = []

    crossref_result = crossref.lookup(article)
    results.append(crossref_result)

    doaj_result = doaj.lookup(article)
    results.append(doaj_result)

    best_so_far = max(r.confidence for r in results)
    if best_so_far < FALLBACK_THRESHOLD:
        web_result = websearch.lookup(article)
        results.append(web_result)

    return aggregate(results)

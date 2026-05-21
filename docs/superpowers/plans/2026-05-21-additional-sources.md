# Additional Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenAlex and Sherpa Romeo as peer-review lookup sources, increasing coverage and confidence for articles Crossref/DOAJ miss.

**Architecture:** Each new source follows the existing pattern — a `checker/sources/{name}.py` module with a single `lookup(article: ArticleInput) -> SourceResult` function. The pipeline in `checker/pipeline.py` is updated to call them in sequence. OpenAlex runs always (free, no key, 250M works). Sherpa Romeo runs only when an ISSN is present (ISSN-indexed, requires free API key).

**Tech Stack:** Python 3.12, `requests`, `responses` (test mocking), existing `models.py` types

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `checker/sources/openalex.py` | Create | OpenAlex REST API lookup by DOI or title |
| `checker/sources/sherpa.py` | Create | Sherpa Romeo v2 API lookup by ISSN |
| `checker/pipeline.py` | Modify | Add OpenAlex (always) and Sherpa Romeo (if ISSN present) |
| `tests/test_openalex.py` | Create | Mocked integration tests for OpenAlex |
| `tests/test_sherpa.py` | Create | Mocked integration tests for Sherpa Romeo |
| `.env.example` | Modify | Add `SHERPA_API_KEY` |
| `README.md` | Modify | Document new sources and Sherpa API key |

---

## Task 1: OpenAlex Source

**Files:**
- Create: `checker/sources/openalex.py`
- Create: `tests/test_openalex.py`

OpenAlex API docs: `https://docs.openalex.org/api-entities/works`
- DOI filter: `GET https://api.openalex.org/works?filter=doi:{doi}&mailto={email}`
- Title search: `GET https://api.openalex.org/works?search={title}&per-page=1&mailto={email}`
- No API key needed; `mailto` param enables polite pool (higher rate limits)
- Response shape: `{"results": [{...}], "meta": {"count": N}}`
- Work object fields used: `type`, `primary_location.source.type`, `primary_location.source.is_in_doaj`, `display_name`

Confidence logic:
- `type == "article"` AND `primary_location.source.type == "journal"` AND `is_in_doaj == True` → confidence 0.95
- `type == "article"` AND `primary_location.source.type == "journal"` → confidence 0.80
- `type == "article"` AND source is not a journal (repository, preprint server) → confidence 0.30, peer_reviewed=None (inconclusive — could be preprint)
- any other type → peer_reviewed=False, confidence 0.70
- 0 results → not found

- [ ] **Step 1: Write failing tests**

```python
# tests/test_openalex.py
import os
import requests
import responses
from unittest.mock import patch
from models import ArticleInput
from checker.sources.openalex import lookup

BASE = "https://api.openalex.org/works"

JOURNAL_ARTICLE_RESPONSE = {
    "results": [{
        "id": "https://openalex.org/W123",
        "type": "article",
        "display_name": "Some Article",
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S123",
                "type": "journal",
                "display_name": "Some Journal",
                "is_in_doaj": False,
            }
        },
    }],
    "meta": {"count": 1},
}

DOAJ_ARTICLE_RESPONSE = {
    "results": [{
        "id": "https://openalex.org/W456",
        "type": "article",
        "display_name": "OA Article",
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S456",
                "type": "journal",
                "display_name": "Open Access Journal",
                "is_in_doaj": True,
            }
        },
    }],
    "meta": {"count": 1},
}

PREPRINT_RESPONSE = {
    "results": [{
        "id": "https://openalex.org/W789",
        "type": "article",
        "display_name": "A Preprint",
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S789",
                "type": "repository",
                "display_name": "bioRxiv",
                "is_in_doaj": False,
            }
        },
    }],
    "meta": {"count": 1},
}


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_journal_article_peer_reviewed():
    responses.add(responses.GET, BASE, json=JOURNAL_ARTICLE_RESPONSE)
    result = lookup(ArticleInput(doi="10.1234/test"))
    assert result.source == "openalex"
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence == 0.80


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_doaj_journal_gets_higher_confidence():
    responses.add(responses.GET, BASE, json=DOAJ_ARTICLE_RESPONSE)
    result = lookup(ArticleInput(doi="10.1234/oa"))
    assert result.peer_reviewed is True
    assert result.confidence == 0.95


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_preprint_inconclusive():
    responses.add(responses.GET, BASE, json=PREPRINT_RESPONSE)
    result = lookup(ArticleInput(doi="10.1234/pre"))
    assert result.found is True
    assert result.peer_reviewed is None
    assert result.confidence == 0.30


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_not_found():
    responses.add(responses.GET, BASE, json={"results": [], "meta": {"count": 0}})
    result = lookup(ArticleInput(doi="10.9999/missing"))
    assert result.found is False
    assert result.peer_reviewed is None
    assert result.confidence == 0.0


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_title_fallback():
    responses.add(responses.GET, BASE, json=JOURNAL_ARTICLE_RESPONSE)
    result = lookup(ArticleInput(title="Some Article"))
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence <= 0.5


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_network_error_returns_safe_result():
    responses.add(responses.GET, BASE, body=requests.exceptions.ConnectionError("timeout"))
    result = lookup(ArticleInput(doi="10.1234/err"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence


def test_no_doi_or_title_returns_not_found():
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.found is False
    assert result.confidence == 0.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_openalex.py -v
```

Expected: `ImportError` — module does not exist.

- [ ] **Step 3: Implement checker/sources/openalex.py**

```python
import os
import requests
from models import ArticleInput, SourceResult

BASE_URL = "https://api.openalex.org/works"


def _email() -> str:
    return os.getenv("CROSSREF_EMAIL", "user@example.com")


def lookup(article: ArticleInput) -> SourceResult:
    try:
        if article.doi:
            return _lookup_by_doi(article.doi)
        if article.title:
            return _lookup_by_title(article.title)
    except requests.RequestException as e:
        return SourceResult(
            source="openalex", found=False, peer_reviewed=None,
            confidence=0.0, evidence=f"Network error: {e}",
        )
    return SourceResult(
        source="openalex", found=False, peer_reviewed=None,
        confidence=0.0, evidence="No DOI or title to query",
    )


def _lookup_by_doi(doi: str) -> SourceResult:
    resp = requests.get(
        BASE_URL,
        params={"filter": f"doi:{doi}", "mailto": _email()},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return SourceResult(
            source="openalex", found=False, peer_reviewed=None,
            confidence=0.0, evidence="DOI not found in OpenAlex",
        )
    return _parse_work(results[0])


def _lookup_by_title(title: str) -> SourceResult:
    resp = requests.get(
        BASE_URL,
        params={"search": title, "per-page": 1, "mailto": _email()},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return SourceResult(
            source="openalex", found=False, peer_reviewed=None,
            confidence=0.0, evidence="Title not found in OpenAlex",
        )
    result = _parse_work(results[0])
    return SourceResult(
        source=result.source, found=result.found, peer_reviewed=result.peer_reviewed,
        confidence=min(result.confidence, 0.5),
        evidence=result.evidence + " (title match — lower confidence)",
    )


def _parse_work(work: dict) -> SourceResult:
    work_type = work.get("type", "")
    name = work.get("display_name", "unknown")
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    source_type = source.get("type", "")
    source_name = source.get("display_name", "unknown source")
    is_in_doaj = source.get("is_in_doaj", False)

    if work_type == "article" and source_type == "journal":
        confidence = 0.95 if is_in_doaj else 0.80
        doaj_note = " (DOAJ-indexed)" if is_in_doaj else ""
        return SourceResult(
            source="openalex", found=True, peer_reviewed=True,
            confidence=confidence,
            evidence=f"Journal article in '{source_name}'{doaj_note}",
        )
    if work_type == "article" and source_type != "journal":
        return SourceResult(
            source="openalex", found=True, peer_reviewed=None,
            confidence=0.30,
            evidence=f"Article hosted on '{source_name}' (type: {source_type}) — may be preprint",
        )
    return SourceResult(
        source="openalex", found=True, peer_reviewed=False,
        confidence=0.70,
        evidence=f"Work type is '{work_type}', not a journal article",
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_openalex.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add checker/sources/openalex.py tests/test_openalex.py
git commit -m "feat: add OpenAlex source lookup"
```

---

## Task 2: Sherpa Romeo Source

**Files:**
- Create: `checker/sources/sherpa.py`
- Create: `tests/test_sherpa.py`

Sherpa Romeo v2 API docs: `https://v2.sherpa.ac.uk/api/`
- Register for free API key at `https://v2.sherpa.ac.uk/cgi/register`
- ISSN lookup: `GET https://v2.sherpa.ac.uk/cgi/retrieve?item-type=publication&api-key={key}&format=Json&filter=[["issn","equals","{issn}"]]`
- Response: `{"items": [...], "total_results": N}`
- Any hit = journal is in Sherpa Romeo = almost certainly peer-reviewed → confidence 0.80
- No ISSN → skip (Sherpa Romeo is ISSN-indexed; title search is unreliable for journal matching)
- Missing API key → return skip result with clear message

- [ ] **Step 1: Write failing tests**

```python
# tests/test_sherpa.py
import os
import requests
import responses
from unittest.mock import patch
from models import ArticleInput
from checker.sources.sherpa import lookup

BASE = "https://v2.sherpa.ac.uk/cgi/retrieve"

FOUND_RESPONSE = {
    "items": [{
        "id": 1234,
        "title": [{"title": "Some Journal", "language": "en"}],
        "issns": [{"issn": "1234-5678", "type": "print"}],
    }],
    "total_results": 1,
}

NOT_FOUND_RESPONSE = {"items": [], "total_results": 0}


@responses.activate
@patch.dict(os.environ, {"SHERPA_API_KEY": "test-key"})
def test_issn_found_returns_peer_reviewed():
    responses.add(responses.GET, BASE, json=FOUND_RESPONSE)
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.source == "sherpa"
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence == 0.80


@responses.activate
@patch.dict(os.environ, {"SHERPA_API_KEY": "test-key"})
def test_issn_not_found():
    responses.add(responses.GET, BASE, json=NOT_FOUND_RESPONSE)
    result = lookup(ArticleInput(issn="9999-9999"))
    assert result.found is False
    assert result.peer_reviewed is None
    assert result.confidence == 0.0


def test_no_issn_skips_lookup():
    result = lookup(ArticleInput(doi="10.1234/test"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "No ISSN" in result.evidence


@patch.dict(os.environ, {"SHERPA_API_KEY": ""})
def test_missing_api_key_skips_lookup():
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "SHERPA_API_KEY" in result.evidence


@responses.activate
@patch.dict(os.environ, {"SHERPA_API_KEY": "test-key"})
def test_network_error_returns_safe_result():
    responses.add(responses.GET, BASE, body=requests.exceptions.ConnectionError("timeout"))
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_sherpa.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement checker/sources/sherpa.py**

```python
import json
import os
import requests
from models import ArticleInput, SourceResult

BASE_URL = "https://v2.sherpa.ac.uk/cgi/retrieve"


def lookup(article: ArticleInput) -> SourceResult:
    if not article.issn:
        return SourceResult(
            source="sherpa", found=False, peer_reviewed=None,
            confidence=0.0, evidence="No ISSN available for Sherpa Romeo lookup",
        )
    api_key = os.getenv("SHERPA_API_KEY", "")
    if not api_key:
        return SourceResult(
            source="sherpa", found=False, peer_reviewed=None,
            confidence=0.0, evidence="SHERPA_API_KEY not configured — skipping Sherpa Romeo",
        )
    try:
        return _lookup_by_issn(article.issn, api_key)
    except requests.RequestException as e:
        return SourceResult(
            source="sherpa", found=False, peer_reviewed=None,
            confidence=0.0, evidence=f"Network error: {e}",
        )


def _lookup_by_issn(issn: str, api_key: str) -> SourceResult:
    filter_param = json.dumps([["issn", "equals", issn]])
    resp = requests.get(
        BASE_URL,
        params={
            "item-type": "publication",
            "api-key": api_key,
            "format": "Json",
            "filter": filter_param,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("total_results", 0) > 0:
        item = data["items"][0]
        titles = item.get("title", [])
        journal_name = titles[0]["title"] if titles else "unknown journal"
        return SourceResult(
            source="sherpa", found=True, peer_reviewed=True,
            confidence=0.80,
            evidence=f"Journal '{journal_name}' (ISSN {issn}) found in Sherpa Romeo",
        )
    return SourceResult(
        source="sherpa", found=False, peer_reviewed=None,
        confidence=0.0, evidence=f"ISSN {issn} not found in Sherpa Romeo",
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_sherpa.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add checker/sources/sherpa.py tests/test_sherpa.py
git commit -m "feat: add Sherpa Romeo source lookup"
```

---

## Task 3: Update Pipeline

**Files:**
- Modify: `checker/pipeline.py`

Current pipeline: Crossref → DOAJ → [if < 0.6] websearch

New pipeline: Crossref → DOAJ → OpenAlex → [if ISSN] Sherpa Romeo → [if < 0.6] websearch

OpenAlex always runs (free, no key, complements Crossref with different coverage). Sherpa Romeo runs only when article has an ISSN — it's ISSN-indexed so no benefit without one.

- [ ] **Step 1: Verify current tests pass before touching pipeline**

```bash
pytest -m "not network" -v
```

Expected: all tests PASS.

- [ ] **Step 2: Update checker/pipeline.py**

```python
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
```

- [ ] **Step 3: Verify import works**

```bash
python -c "from checker.pipeline import check; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Run full test suite to confirm no regressions**

```bash
pytest -m "not network" -v
```

Expected: all tests PASS. (Pipeline itself has no unit tests — it is exercised indirectly through network tests.)

- [ ] **Step 5: Commit**

```bash
git add checker/pipeline.py
git commit -m "feat: add OpenAlex and Sherpa Romeo to pipeline"
```

---

## Task 4: Config and Docs

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Update .env.example**

Replace contents with:

```
CROSSREF_EMAIL=your@email.com
BRAVE_API_KEY=your_key_here
SHERPA_API_KEY=your_key_here
```

- [ ] **Step 2: Update sources table in README.md**

Find the sources table and replace with:

```markdown
| Source | Confidence | Notes |
|--------|-----------|-------|
| DOAJ | 0.95 | Indexes only peer-reviewed OA journals |
| OpenAlex (DOAJ-indexed) | 0.95 | Cross-validated with DOAJ via OpenAlex metadata |
| Crossref | 0.75 / 0.55 | Inferred from `journal-article` type; citations boost confidence |
| OpenAlex | 0.80 | Journal article in OpenAlex non-DOAJ journal |
| Sherpa Romeo | 0.80 | Journal found in Sherpa Romeo publisher database |
| Brave Search | 0.50 | Heuristic — PubMed/Scopus/WoS signals in top 3 results |
| OpenAlex (preprint) | 0.30 | Article found but hosted on repository — may be preprint |
```

Also add `SHERPA_API_KEY` to the Setup section after `BRAVE_API_KEY`:

```markdown
SHERPA_API_KEY=your_key_here         # Optional — enables Sherpa Romeo journal lookup (free registration at v2.sherpa.ac.uk/cgi/register)
```

- [ ] **Step 3: Run smoke test to confirm pipeline wires through**

```bash
python main.py --doi "10.1038/nature12373"
```

Expected: verdict printed, openalex source visible in evidence (no crash).

- [ ] **Step 4: Commit**

```bash
git add .env.example README.md
git commit -m "docs: add Sherpa Romeo API key docs and update source confidence table"
```

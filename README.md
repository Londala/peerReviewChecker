# Peer Review Checker

Checks whether a journal article is peer-reviewed by querying Crossref, DOAJ, OpenAlex, Sherpa Romeo, and Brave Search. Available as a desktop GUI or CLI.

## Requirements

- Python 3.10+
- Linux, macOS, or Windows (WSL supported)
- `tkinter` — usually bundled with Python; on Ubuntu/Debian: `sudo apt-get install python3-tk`

## Setup

```bash
git clone <repo-url>
cd peerReviewChecker
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set:

```
CROSSREF_EMAIL=your@email.com       # Required for Crossref and OpenAlex polite pool
BRAVE_API_KEY=your_key_here         # Optional — enables web search fallback
SHERPA_API_KEY=your_key_here        # Optional — enables Sherpa Romeo journal lookup
```

Brave API key is free at [brave.com/search/api](https://brave.com/search/api) (2000 req/month). Sherpa Romeo key is free at [v2.sherpa.ac.uk/cgi/register](https://v2.sherpa.ac.uk/cgi/register). Without optional keys, those sources are skipped.

## GUI

```bash
python gui.py
```

Enter any combination of Title, DOI, ISSN, Author, and Journal, then click **Check**. Results appear in the table with verdict symbol, confidence, and a note for low-confidence results. When a DOI is used, the table shows the resolved article title with the DOI in parentheses. Click any row to expand source details. Use **Export CSV** or **Export JSON** to save results.

**Batch mode:** switch to *Batch File*, browse for a CSV or JSON file (same format as CLI batch below), and click **Check**. Rows appear as each article completes.

## CLI Usage

### Single article

```bash
python main.py --doi "10.1038/nature12373"
python main.py --title "Observation of a new boson at a mass of 125 GeV"
python main.py --issn "0028-0836"
python main.py --title "..." --author "Higgs" --journal "Nature"
```

### JSON output

```bash
python main.py --doi "10.1038/nature12373" --json
```

```json
{
  "peer_reviewed": true,
  "confidence": 0.75,
  "sources": [
    {
      "source": "crossref",
      "found": true,
      "peer_reviewed": true,
      "confidence": 0.75,
      "evidence": "Journal article in 'Nature' with 1770 citations (peer-review inferred from type)"
    }
  ]
}
```

### Interactive mode

```bash
python main.py
```

Prompts for title, DOI, and ISSN.

### Batch file

```bash
python main.py --file articles.csv
python main.py --file articles.json --json
```

**CSV format** (header required, any subset of columns):

```csv
title,doi,issn,author,journal
Observation of a new boson,10.1038/nature12373,,Higgs,Nature
Some Other Article,,,Smith,
```

**JSON format:**

```json
[
  {"title": "Observation of a new boson", "doi": "10.1038/nature12373"},
  {"title": "Some Other Article", "author": "Smith"}
]
```

Results stream to stdout as each article completes. Errors print to stderr; processing continues.

## Output

| Symbol | Meaning |
|--------|---------|
| `✓` | Peer-reviewed (confidence ≥ 60%) |
| `✗` | Not peer-reviewed (confidence ≥ 60%) |
| `~` | Likely not reviewed (confidence < 40%) |
| `?` | Inconclusive |

Confidence ranges from 0–1. Sources:

| Source | Confidence | Notes |
|--------|-----------|-------|
| DOAJ | 0.95 | Indexes only peer-reviewed OA journals |
| OpenAlex (DOAJ-indexed) | 0.95 | Cross-validated with DOAJ via OpenAlex metadata |
| Crossref | 0.75 / 0.55 | Inferred from `journal-article` type; citations boost confidence |
| OpenAlex | 0.80 | Journal article in OpenAlex non-DOAJ journal |
| Sherpa Romeo | 0.80 | Journal found in Sherpa Romeo publisher database (requires ISSN) |
| Brave Search | 0.50 | Heuristic — PubMed/Scopus/WoS signals in top 3 results |
| OpenAlex (preprint) | 0.30 | Article found but hosted on repository — may be preprint |

Verdict is inconclusive if best confidence < 0.6.

## Building a standalone executable

Executables must be built on the target platform (Windows exe on Windows, macOS app on Mac).

### macOS / Linux

```bash
bash build.sh
```

Output: `dist/PeerReviewChecker` (Linux) or `dist/PeerReviewChecker.app` (macOS).

### Windows

```bat
build.bat
```

Output: `dist\PeerReviewChecker.exe`.

### Distributing

Place a `.env` file next to the executable (or `.app` on Mac) with API keys filled in. Users who don't have API keys can omit `BRAVE_API_KEY` and `SHERPA_API_KEY` — those sources will be skipped. `CROSSREF_EMAIL` should always be set.

```
CROSSREF_EMAIL=user@example.com
BRAVE_API_KEY=optional
SHERPA_API_KEY=optional
```

On macOS, if Gatekeeper blocks the app: right-click → Open → Open anyway.

## Running tests

```bash
pytest -m "not network"          # fast, no network
pytest -m network                # real API calls (requires internet)
```

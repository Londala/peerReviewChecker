# GUI Design Spec

**Date:** 2026-05-21
**Feature:** customtkinter GUI for peer review checker

---

## Goal

A standalone `gui.py` at the project root that exposes all article inputs and batch file processing in a desktop GUI. Runs alongside `main.py` — the CLI is unchanged.

---

## Architecture

Single file: `gui.py`. Launches a `customtkinter.CTk` window. Imports `checker.pipeline.check`, `checker.input.normalize`, `batch.parse_file`, and `batch.stream_check` directly (same process, no subprocess). Calls `load_dotenv()` at startup. `customtkinter` added to `requirements.txt`.

---

## Layout

Mode toggle at top: two `CTkRadioButton` widgets ("Single Article" / "Batch File"). Toggling swaps the input panel.

**Single Article panel:**
- Five `CTkEntry` fields: Title, DOI, ISSN, Author, Journal

**Batch File panel:**
- One `CTkEntry` (file path, read-only) + "Browse" `CTkButton` → `filedialog.askopenfilename` filtered to `.csv` / `.json`

Below input panel:
- "Check" `CTkButton`
- Red `CTkLabel` for validation/file errors (hidden when no error)
- Status `CTkLabel` ("Checking…") shown while running, hidden otherwise

Results area (`CTkScrollableFrame`):
- Header row: Article | Verdict | Confidence | Note
- One row per result; clicking a row reveals per-source evidence below the table
- Verdict symbols: ✓ (peer-reviewed) / ✗ (not peer-reviewed) / ? (inconclusive) / ! (lookup failed)
- Note column: populated only when confidence < 0.6 — short reason extracted from best-confidence source evidence ("title match", "preprint", etc.); blank otherwise

Export row (hidden until at least one result exists):
- "Export CSV" button
- "Export JSON" button

---

## Data Flow

1. User clicks "Check"
2. Button disabled, status label shown
3. **Single mode:** `normalize()` called → `ValidationError` shows red error label, stops. On success: `pipeline.check(article)` → one table row appended
4. **Batch mode:** `parse_file(path)` → `FileNotFoundError`/`ValueError` shows red error label, stops. On success: iterate `stream_check(articles)`, append one row per article, call `root.update()` between rows so progress is visible
5. Button re-enabled, status label hidden, Export buttons revealed

All processing on main thread (blocking). `root.update()` between batch rows provides visual progress without threading complexity.

---

## Results Table Detail

Clicking a table row expands a detail section below the table showing per-source evidence for that article. Only one row expanded at a time. Clicking the same row again collapses it.

---

## Error Handling

| Error | Behavior |
|-------|----------|
| `ValidationError` (bad ISSN, no identifiers) | Red label below inputs; button re-enabled; no row added |
| `FileNotFoundError` / bad file format | Red label; button re-enabled |
| Per-article pipeline error (mid-batch network failure) | Row added with verdict `!`, note "lookup failed"; processing continues |

---

## Export

**Export CSV:** `filedialog.asksaveasfilename` (`.csv`). Columns: `article, verdict, confidence, note, sources_json`. `sources_json` is a JSON-encoded list of per-source dicts (same structure as `format_json` output).

**Export JSON:** `filedialog.asksaveasfilename` (`.json`). Array of objects: `{article, verdict, confidence, note, sources[]}` where `sources` matches `format_json` structure.

Export buttons hidden until at least one result exists.

---

## Note Extraction Logic

Given a `Verdict`, derive the Note column value:

1. If `confidence >= 0.6`: return `""`
2. Find the source result with the highest confidence
3. Scan its `evidence` string for known phrases:
   - `"title match"` → `"title match"`
   - `"preprint"` → `"preprint"`
   - `"not a journal article"` → `"non-article"`
4. If no phrase matches: return `"low confidence"`

---

## Files Changed

| File | Action |
|------|--------|
| `gui.py` | Create |
| `requirements.txt` | Add `customtkinter` |

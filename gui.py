import csv
import json
import os
import sys
from pathlib import Path

import customtkinter as ctk
from dotenv import load_dotenv

from batch import parse_file, stream_check
from checker.input import ValidationError, normalize
from checker.pipeline import check
from models import Verdict

# When frozen by PyInstaller, load .env from the executable's directory
# rather than the extraction temp dir.
_app_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
load_dotenv(_app_dir / ".env")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0d1117"
SURFACE  = "#161b22"
SURFACE2 = "#21262d"
BORDER   = "#30363d"
ACCENT   = "#388bfd"
ACCENT_D = "#1f6feb"
TEXT     = "#e6edf3"
MUTED    = "#7d8590"
SUCCESS  = "#3fb950"
DANGER   = "#f85149"
WARN     = "#d29922"
ROW_A    = "#161b22"
ROW_B    = "#0d1117"
ROW_SEL  = "#1c2d40"

SYMBOL     = {True: "✓", False: "✗", None: "?"}
SYM_COLOR  = {"✓": SUCCESS, "✗": DANGER, "?": WARN, "~": "#e07b54", "!": DANGER}

COL_WIDTHS = (0, 72, 100, 130)   # article=flexible, verdict, confidence, note


def _extract_note(verdict: Verdict | None) -> str:
    if verdict is None:
        return ""
    if verdict.peer_reviewed is True and verdict.confidence >= 0.6:
        citations = next(
            (s.citations for s in verdict.sources if s.citations is not None), None
        )
        return f"{citations:,} citations" if citations else ""
    if verdict.confidence >= 0.6:
        return ""
    if not verdict.sources:
        return "low confidence"
    best = max(verdict.sources, key=lambda s: s.confidence)
    ev = best.evidence.lower()
    if "title match" in ev:
        return "title match"
    if "preprint" in ev:
        return "preprint"
    if "not a journal article" in ev:
        return "non-article"
    return "low confidence"


def _sources_list(verdict: Verdict | None) -> list:
    if not verdict:
        return []
    return [
        {
            "source": s.source, "found": s.found,
            "peer_reviewed": s.peer_reviewed,
            "confidence": round(s.confidence, 4),
            "evidence": s.evidence,
        }
        for s in verdict.sources
    ]


def _col_conf(frame: ctk.CTkBaseClass | ctk.CTkScrollableFrame) -> None:
    frame.grid_columnconfigure(0, weight=1)
    for i, w in enumerate(COL_WIDTHS[1:], start=1):
        frame.grid_columnconfigure(i, minsize=w, weight=0)


_ENV_FIELDS = [
    ("CROSSREF_EMAIL",  "Email for Crossref / OpenAlex polite pool (required)"),
    ("BRAVE_API_KEY",   "Brave Search API key — optional, enables web fallback"),
    ("SHERPA_API_KEY",  "Sherpa Romeo API key — optional, enables journal lookup"),
]


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.geometry("520x260")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.grab_set()

        self._entries: dict[str, ctk.CTkEntry] = {}
        self.grid_columnconfigure(1, weight=1)

        for i, (key, hint) in enumerate(_ENV_FIELDS):
            ctk.CTkLabel(
                self, text=key + ":", text_color=MUTED,
                font=ctk.CTkFont(size=13), width=140, anchor="e",
            ).grid(row=i, column=0, padx=(16, 8), pady=(14 if i == 0 else 6, 0), sticky="e")

            entry = ctk.CTkEntry(
                self, fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                font=ctk.CTkFont(size=13), show="*" if "KEY" in key else "",
            )
            entry.insert(0, os.getenv(key, ""))
            entry.grid(row=i, column=1, padx=(0, 16), pady=(14 if i == 0 else 6, 0), sticky="ew")

            ctk.CTkLabel(
                self, text=hint, text_color=MUTED,
                font=ctk.CTkFont(size=11), anchor="w",
            ).grid(row=i, column=2, padx=(0, 16), pady=(14 if i == 0 else 6, 0), sticky="w")

            self._entries[key] = entry

        btn_row = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        btn_row.grid(row=len(_ENV_FIELDS), column=0, columnspan=3, sticky="ew", pady=(16, 10))
        ctk.CTkButton(
            btn_row, text="Save", width=100,
            fg_color=ACCENT_D, hover_color=ACCENT, text_color=TEXT,
            command=self._save,
        ).pack(side="left", padx=16)
        ctk.CTkButton(
            btn_row, text="Cancel", width=100,
            fg_color=SURFACE2, hover_color=BORDER, text_color=TEXT,
            command=self.destroy,
        ).pack(side="left", padx=0)

    def _save(self) -> None:
        env_path = _app_dir / ".env"
        lines = []
        for key, entry in self._entries.items():
            val = entry.get().strip()
            lines.append(f"{key}={val}")
            if val:
                os.environ[key] = val
            else:
                os.environ.pop(key, None)
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        load_dotenv(env_path, override=True)
        self.destroy()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Peer Review Checker")
        self.geometry("900x700")
        self.minsize(640, 480)
        self.configure(fg_color=BG)

        self._results: list[dict] = []
        self._row_frames: list[ctk.CTkFrame] = []
        self._selected: int | None = None
        self._mode = ctk.StringVar(value="single")
        self._batchpath = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build()
        self._switch_mode()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_mode_toggle()
        self._build_input_area()
        self._build_action_row()
        self._build_results()
        self._build_detail()
        self._build_export()

    def _build_mode_toggle(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=SURFACE2, corner_radius=0, height=38)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkLabel(bar, text="Mode:", text_color=MUTED,
                     font=ctk.CTkFont(size=13)).place(x=18, rely=0.5, anchor="w")
        for x, text, val in [(80, "Single Article", "single"), (232, "Batch File", "batch")]:
            ctk.CTkRadioButton(
                bar, text=text, variable=self._mode, value=val,
                command=self._switch_mode, text_color=TEXT,
                fg_color=ACCENT, hover_color=ACCENT_D,
            ).place(x=x, rely=0.5, anchor="w")

    def _build_input_area(self) -> None:
        self._input_area = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._input_area.grid(row=1, column=0, sticky="ew")
        self._input_area.grid_columnconfigure(0, weight=1)

        # Single panel: 5 entry fields
        self._single = ctk.CTkFrame(self._input_area, fg_color=BG, corner_radius=0)
        self._single.grid_columnconfigure(1, weight=1)
        self._entries: dict[str, ctk.CTkEntry] = {}
        for i, (label, key) in enumerate([
            ("Title", "title"), ("DOI", "doi"), ("ISSN", "issn"),
            ("Author", "author"), ("Journal", "journal"),
        ]):
            ctk.CTkLabel(
                self._single, text=label + ":", text_color=MUTED, width=68, anchor="e",
            ).grid(row=i, column=0, padx=(16, 6), pady=3, sticky="e")
            entry = ctk.CTkEntry(
                self._single, fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
            )
            entry.grid(row=i, column=1, padx=(0, 16), pady=3, sticky="ew")
            self._entries[key] = entry

        # Batch panel: file picker
        self._batch = ctk.CTkFrame(self._input_area, fg_color=BG, corner_radius=0)
        self._batch.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self._batch, text="File:", text_color=MUTED, width=68, anchor="e",
        ).grid(row=0, column=0, padx=(16, 6), pady=14, sticky="e")
        self._path_entry = ctk.CTkEntry(
            self._batch, fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, state="disabled",
        )
        self._path_entry.grid(row=0, column=1, padx=(0, 6), pady=14, sticky="ew")
        ctk.CTkButton(
            self._batch, text="Browse", width=80,
            fg_color=SURFACE2, hover_color=BORDER, text_color=TEXT,
            command=self._browse,
        ).grid(row=0, column=2, padx=(0, 16), pady=14)

    def _build_action_row(self) -> None:
        row = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        row.grid(row=2, column=0, sticky="ew")
        self._btn = ctk.CTkButton(
            row, text="Check", width=110,
            fg_color=ACCENT_D, hover_color=ACCENT,
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT,
            command=self._check,
        )
        self._btn.pack(side="left", padx=16, pady=10)
        self._status_lbl = ctk.CTkLabel(row, text="", text_color=MUTED,
                                        font=ctk.CTkFont(size=13))
        self._status_lbl.pack(side="left", padx=4)
        self._error_lbl = ctk.CTkLabel(row, text="", text_color=DANGER,
                                       font=ctk.CTkFont(size=13))
        self._error_lbl.pack(side="left", padx=4)
        ctk.CTkButton(
            row, text="⚙ Settings", width=100,
            fg_color=SURFACE2, hover_color=BORDER, text_color=MUTED,
            font=ctk.CTkFont(size=13),
            command=lambda: SettingsWindow(self),
        ).pack(side="right", padx=16, pady=10)

    def _build_results(self) -> None:
        outer = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8)
        outer.grid(row=3, column=0, sticky="nsew", padx=16, pady=(4, 4))
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        # Header
        hdr = ctk.CTkFrame(outer, fg_color=SURFACE2, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        _col_conf(hdr)
        for col, (text, anchor) in enumerate([
            ("Article", "w"), ("Verdict", "center"),
            ("Confidence", "center"), ("Note", "w"),
        ]):
            ctk.CTkLabel(
                hdr, text=text, text_color=MUTED,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=COL_WIDTHS[col] or 0, anchor=anchor,
            ).grid(row=0, column=col, padx=(12 if col == 0 else 2, 2), pady=6,
                   sticky="w" if col == 0 else "ew")

        # Scrollable body
        self._scroll = ctk.CTkScrollableFrame(outer, fg_color=SURFACE, corner_radius=0)
        self._scroll.grid(row=1, column=0, sticky="nsew")
        _col_conf(self._scroll)

        self._placeholder = ctk.CTkLabel(
            self._scroll, text="No results yet.",
            text_color=MUTED, font=ctk.CTkFont(size=13),
        )
        self._placeholder.grid(row=0, column=0, columnspan=4, pady=24)

    def _build_detail(self) -> None:
        self._detail = ctk.CTkFrame(self, fg_color=SURFACE2, corner_radius=8)
        self._detail_box = ctk.CTkTextbox(
            self._detail, fg_color=SURFACE2, text_color=TEXT,
            font=ctk.CTkFont(family="Courier", size=12),
            height=110, state="disabled",
        )
        self._detail_box.pack(fill="both", expand=True, padx=10, pady=6)

    def _build_export(self) -> None:
        self._export_row = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        for text, cmd in [("Export CSV", self._export_csv),
                          ("Export JSON", self._export_json)]:
            ctk.CTkButton(
                self._export_row, text=text, width=110,
                fg_color=SURFACE2, hover_color=BORDER, text_color=TEXT,
                command=cmd,
            ).pack(side="left", padx=(16 if text == "Export CSV" else 0, 6), pady=8)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _switch_mode(self) -> None:
        if self._mode.get() == "single":
            self._batch.grid_remove()
            self._single.grid(row=0, column=0, sticky="ew", pady=6)
        else:
            self._single.grid_remove()
            self._batch.grid(row=0, column=0, sticky="ew")
        self._error_lbl.configure(text="")

    def _browse(self) -> None:
        path = ctk.filedialog.askopenfilename(
            filetypes=[("CSV/JSON files", "*.csv *.json"), ("All files", "*.*")],
        )
        if path:
            self._batchpath = path
            self._path_entry.configure(state="normal")
            self._path_entry.delete(0, "end")
            self._path_entry.insert(0, path)
            self._path_entry.configure(state="disabled")
            self._error_lbl.configure(text="")

    def _check(self) -> None:
        self._error_lbl.configure(text="")
        self._btn.configure(state="disabled")
        self._status_lbl.configure(text="Checking…")
        self.update()
        try:
            if self._mode.get() == "single":
                self._check_single()
            else:
                self._check_batch()
        finally:
            self._btn.configure(state="normal")
            self._status_lbl.configure(text="")
        if self._results:
            self._export_row.grid(row=5, column=0, sticky="ew")

    def _check_single(self) -> None:
        try:
            article = normalize(
                title=self._entries["title"].get() or None,
                doi=self._entries["doi"].get() or None,
                issn=self._entries["issn"].get() or None,
                author=self._entries["author"].get() or None,
                journal=self._entries["journal"].get() or None,
            )
        except ValidationError as e:
            self._error_lbl.configure(text=f"⚠ {e}")
            return
        verdict = check(article)
        if article.doi and verdict.title:
            label = f"{verdict.title} ({article.doi})"
        else:
            label = article.doi or article.title or article.issn or "article"
        self._add_row(label, verdict, None)

    def _check_batch(self) -> None:
        if not self._batchpath:
            self._error_lbl.configure(text="⚠ No file selected.")
            return
        try:
            articles = list(parse_file(self._batchpath))
        except (ValueError, FileNotFoundError) as e:
            self._error_lbl.configure(text=f"⚠ {e}")
            return
        for article, verdict, error in stream_check(articles):
            label = article.doi or article.title or article.issn or "article"
            self._add_row(label, verdict, error)
            self.update()

    # ── Table ─────────────────────────────────────────────────────────────────

    def _add_row(self, label: str, verdict: Verdict | None, error: Exception | None) -> None:
        idx = len(self._results)
        if error:
            sym = "!"
        elif verdict and verdict.confidence < 0.4:
            sym = "~"
        else:
            sym = SYMBOL.get(verdict.peer_reviewed if verdict else None, "?")
        conf = f"{verdict.confidence:.0%}" if verdict and not error else "—"
        note = "lookup failed" if error else _extract_note(verdict)

        self._results.append({
            "label": label, "verdict": verdict,
            "sym": sym, "conf": conf, "note": note, "error": error,
        })

        if idx == 0:
            self._placeholder.grid_remove()

        bg = ROW_A if idx % 2 == 0 else ROW_B
        rf = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0)
        rf.grid(row=idx, column=0, columnspan=4, sticky="ew", pady=(0, 1))
        _col_conf(rf)

        short = label if len(label) <= 90 else label[:87] + "…"
        cells = [
            (short, TEXT, 0, "w"),
            (sym, SYM_COLOR.get(sym, TEXT), COL_WIDTHS[1], "center"),
            (conf, MUTED, COL_WIDTHS[2], "center"),
            (note, MUTED if (not note or "citations" in note) else WARN, COL_WIDTHS[3], "w"),
        ]
        for col, (text, color, width, anchor) in enumerate(cells):
            lbl = ctk.CTkLabel(
                rf, text=text, text_color=color,
                font=ctk.CTkFont(size=13),
                width=width or 0, anchor=anchor,
            )
            lbl.grid(row=0, column=col,
                     padx=(12 if col == 0 else 2, 2), pady=5,
                     sticky="w" if col == 0 else "ew")
            lbl.bind("<Button-1>", lambda _e, i=idx: self._toggle(i))

        rf.bind("<Button-1>", lambda _e, i=idx: self._toggle(i))
        self._row_frames.append(rf)

    def _toggle(self, idx: int) -> None:
        if self._selected == idx:
            self._selected = None
            self._detail.grid_remove()
            self._restore_bg(idx)
        else:
            if self._selected is not None:
                self._restore_bg(self._selected)
            self._selected = idx
            self._row_frames[idx].configure(fg_color=ROW_SEL)
            self._show_detail(idx)

    def _restore_bg(self, idx: int) -> None:
        self._row_frames[idx].configure(fg_color=ROW_A if idx % 2 == 0 else ROW_B)

    def _show_detail(self, idx: int) -> None:
        r = self._results[idx]
        lines = [f"Article: {r['label']}"]
        if r["error"]:
            lines.append(f"Error: {r['error']}")
        elif r["verdict"]:
            for s in r["verdict"].sources:
                status = "found" if s.found else "not found"
                lines.append(
                    f"[{s.source}] {status} · conf={s.confidence:.2f} · {s.evidence}"
                )
        self._detail_box.configure(state="normal")
        self._detail_box.delete("1.0", "end")
        self._detail_box.insert("end", "\n".join(lines))
        self._detail_box.configure(state="disabled")
        self._detail.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 4))

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        path = ctk.filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["article", "verdict", "confidence", "note", "sources_json"])
            for r in self._results:
                w.writerow([
                    r["label"], r["sym"], r["conf"], r["note"],
                    json.dumps(_sources_list(r["verdict"])),
                ])

    def _export_json(self) -> None:
        path = ctk.filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        data = [
            {
                "article": r["label"], "verdict": r["sym"],
                "confidence": r["conf"], "note": r["note"],
                "sources": _sources_list(r["verdict"]),
            }
            for r in self._results
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    app = App()
    app.mainloop()

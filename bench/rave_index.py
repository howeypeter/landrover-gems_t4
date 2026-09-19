"""Scan all local RAVE PDFs and emit a section->page index markdown file."""
import re
from pathlib import Path
from pypdf import PdfReader

HOME = Path.home()
RAVE = HOME / "Downloads" / "rave" / "rave" / "pdf"
EXTRA = [HOME / "Downloads" / "RAVE ETM.pdf"]
OUT = Path(r"C:\Users\howey\OneDrive\Documents\Claude\Projects\LandRoverV1\docs\rave-index.md")

MODEL = {
    "lj": "Discovery 1", "lp": "Range Rover P38A", "lt": "Discovery 2",
    "ld": "Defender", "ln01": "Freelander 1", "lm": "Range Rover (other)",
    "lh": "(unknown)", "general": "General", "library": "Library",
}


def clean(s: str) -> str:
    s = "".join(c if ord(c) < 128 else "-" for c in s)
    return re.sub(r"\s+", " ", s).strip()


def title_of(text: str) -> str:
    cands = [clean(ln) for ln in text.splitlines()]
    cands = [c for c in cands if len(c) >= 4]
    for c in cands[:8]:
        letters = [ch for ch in c if ch.isalpha()]
        if (letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.75
                and not c.startswith("/")):
            return c
    return cands[0] if cands else ""


def sections(reader):
    out, prev, start, first_title = [], None, None, None
    for i, p in enumerate(reader.pages):
        t = title_of(p.extract_text() or "")
        key = re.sub(r"\s+[A-Z]\d{1,2}$", "", t).strip() if t else ""
        if key != prev:
            if prev is not None:
                out.append((first_title, start + 1, i))
            prev, start, first_title = key, i, t
    if prev is not None:
        out.append((first_title, start + 1, len(reader.pages)))
    return out


pdfs = []
for md in sorted(RAVE.iterdir()):
    if md.is_dir():
        for pdf in sorted(md.glob("*.pdf")):
            pdfs.append((md.name, pdf))
for e in EXTRA:
    if e.exists():
        pdfs.append(("(root)", e))

L = [
    "# RAVE index (auto-generated, LOCAL ONLY - not committed)",
    "",
    "Section->page map of the local RAVE PDFs so we jump straight to a circuit",
    "instead of re-scanning. **RAVE is Land Rover IP; the PDFs are NOT in the repo**",
    "- they live in `~/Downloads/rave/rave/pdf/<model>/` (+ `~/Downloads/RAVE ETM.pdf`).",
    "Open a page with the Read tool (page numbers here are **1-indexed**, matching",
    "the `pages` arg). Titles are auto-extracted from diagram headers (best-effort).",
    "",
    "**Model codes:** `lj`=Discovery 1, `lp`=Range Rover P38A, `lt`=Discovery 2,",
    "`ld`=Defender, `ln01`=Freelander 1.  For the **GEMS Disco-1 use `lj`**.",
    "",
]

cur = None
for model, pdf in pdfs:
    try:
        r = PdfReader(str(pdf))
    except Exception as e:  # noqa: BLE001
        L.append(f"- (could not read {pdf.name}: {e})")
        continue
    if model != cur:
        L.append(f"\n## `{model}` - {MODEL.get(model, '?')}\n")
        cur = model
    rel = pdf.relative_to(HOME) if str(pdf).startswith(str(HOME)) else pdf
    L.append(f"### `{pdf.name}`  ({len(r.pages)} pages)")
    L.append(f"path: `~/{rel.as_posix().split('/', 1)[1] if model=='(root)' else rel.as_posix()}`\n")
    L.append("| pages | section |")
    L.append("|---|---|")
    for title, a, b in sections(r):
        title = (title or "(untitled)")[:90]
        rng = f"{a}" if a == b else f"{a}-{b}"
        L.append(f"| {rng} | {title} |")
    L.append("")

OUT.write_text("\n".join(L), encoding="utf-8")
print("wrote", OUT)
print("pdfs scanned:", len(pdfs), "| lines:", len(L))

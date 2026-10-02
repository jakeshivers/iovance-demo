"""Parse FDA PDFs, chunk by heading, embed, and bulk index."""
import re
from pathlib import Path

from pypdf import PdfReader

from rag.interfaces import BgeEmbedder, OpenSearchStore

DOCS = Path("docs")
CHUNK_WORDS, OVERLAP_WORDS = 380, 38  # ~500 / ~50 tokens at ~1.3 tokens per word
BOILERPLATE = re.compile(r"^(Contains Nonbinding Recommendations|Draft\s*—\s*Not for Implementation|\d+)$")
LINE_NO = re.compile(r"\s+\d{1,3}$")
# (level, pattern): I. or Appendix A / A. or Example 1: / 1. or (1) / a.
HEADINGS = [
    (0, re.compile(r"^([IVX]+)\.\s+([A-Z].*)$")),
    (0, re.compile(r"^(Appendix [A-Z])\.?\s+([A-Z].*)$")),
    (1, re.compile(r"^([A-Z])\.\s+([A-Z].*)$")),
    (1, re.compile(r"^Example (\d+):\s+([A-Z].*)$")),
    (2, re.compile(r"^(?:(\d{1,2})\.|\((\d{1,2})\))\s+([A-Z].*)$")),
    (3, re.compile(r"^([a-z])\.\s+([A-Z].*)$")),
]


def raw_lines(text: str) -> list[str]:
    if "......" in text or "TABLE OF CONTENTS" in text.upper()[:200]:
        return []
    return [l.strip() for l in text.splitlines() if l.strip()]


def page_lines(text: str, numbered: bool) -> list[str]:
    lines = [LINE_NO.sub("", l) for l in raw_lines(text)] if numbered else raw_lines(text)
    return [l for l in lines if not BOILERPLATE.match(l)]


def match_heading(line: str):
    if len(line) > 100 or line.endswith((".", ",", ";")):
        return None
    for level, pat in HEADINGS:
        if m := pat.match(line):
            num, title = next(g for g in m.groups()[:-1] if g), m.groups()[-1]
            return level, num, re.sub(r"(?<=[A-Za-z])\d{1,2}$", "", title).strip()  # drop glued footnote marker
    return None


def sections(path: Path):
    """Yield (section_label, [(word, page), ...]) per heading."""
    nums, label, words = [None] * 4, "Preamble", []
    texts = [p.extract_text() or "" for p in PdfReader(path).pages]
    lines = [l for t in texts for l in raw_lines(t)]
    numbered = bool(lines) and sum(bool(LINE_NO.search(l)) for l in lines) / len(lines) > 0.25  # margin line nos
    for pno, text in enumerate(texts, 1):
        for line in page_lines(text, numbered):
            if h := match_heading(line):
                if words:
                    yield label, words
                level, num, title = h
                nums[level:] = [num] + [None] * (3 - level)
                label, words = ".".join(n for n in nums if n) + " " + title, []
            if words and words[-1][0].endswith("-"):  # rejoin hyphenated line breaks
                first, *rest = line.split()
                words[-1] = (words[-1][0] + first, words[-1][1])
                words += [(w, pno) for w in rest]
            else:
                words += [(w, pno) for w in line.split()]
    if words:
        yield label, words


def chunk(doc: str, path: Path) -> list[dict]:
    out = []
    for label, words in sections(path):
        step = CHUNK_WORDS - OVERLAP_WORDS
        for start in range(0, max(len(words) - OVERLAP_WORDS, 1), step):
            win = words[start:start + CHUNK_WORDS]
            out.append({"doc": doc, "section": label, "page": win[0][1],
                        "text": f"{label}\n" + " ".join(w for w, _ in win)})
    return out


def main():
    embedder, store, total = BgeEmbedder(), OpenSearchStore(), 0
    for path in sorted(DOCS.glob("*.pdf")):
        chunks = chunk(path.stem, path)
        for c, e in zip(chunks, embedder.embed([c["text"] for c in chunks])):
            c["embedding"] = e
        n = store.replace_doc(path.stem, chunks)
        print(f"{path.stem}: {n} chunks")
        total += n
    print(f"total: {total} chunks")


if __name__ == "__main__":
    main()

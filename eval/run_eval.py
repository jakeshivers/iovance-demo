"""Compare retrieval modes x LLMs on the golden set; print a markdown table."""
import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.generate import REFUSAL, answer, make_llm  # noqa: E402
from rag.interfaces import OpenSearchStore  # noqa: E402
from rag.retrieve import CFG  # noqa: E402

MODES = ["vector", "hybrid", "hybrid_rerank"]
POISONED = "zz_poisoned_test"
CITE = re.compile(r"\[(\S+) §(\S+)")


class NoLLM:
    """Retrieval-only run: measures recall and the rerank refusal gate."""
    def complete(self, system, user):
        return ""


def matches(expected: str, doc: str, section: str) -> bool:
    exp_doc, exp_sec = expected.split(" §")
    return doc == exp_doc and (section == exp_sec or section.startswith(exp_sec + " "))


def run(golden: list[dict], mode: str, llm_name: str) -> dict:
    llm = NoLLM() if llm_name == "none" else make_llm(llm_name)
    hit5, cited, refused_ok, lat = [], [], [], []
    for g in golden:
        t = time.perf_counter()
        text, hits = answer(g["q"], llm, mode)
        lat.append(time.perf_counter() - t)
        refused = REFUSAL in text
        refused_ok.append(refused == g["should_refuse"])
        if g["should_refuse"]:
            continue
        hit5.append(any(matches(g["expected_section"], h["doc"], h["section"]) for h in hits[:5]))
        cites = CITE.findall(text)
        cited.append(not refused and any(matches(g["expected_section"], d, s) for d, s in cites))
    pct = lambda xs: f"{100 * sum(xs) / len(xs):.0f}%"
    return {"mode": mode, "llm": llm_name, "recall": sum(hit5) / len(hit5), "recall@5": pct(hit5),
            "citation acc": "n/a" if llm_name == "none" else pct(cited),
            "refusal acc": pct(refused_ok), "p50 latency": f"{statistics.median(lat):.2f}s"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llms", nargs="+", default=["ollama", "anthropic"], help="ollama anthropic none")
    ap.add_argument("--check-baseline", action="store_true", help="exit 1 if hybrid_rerank recall@5 < baseline")
    args = ap.parse_args()

    golden = [json.loads(l) for l in open(Path(__file__).parent / "golden.jsonl")]
    OpenSearchStore().replace_doc(POISONED, [])  # keep the injection test doc out of the eval; re-ingest restores it
    rows = [run(golden, m, l) for l in args.llms for m in MODES]

    cols = ["mode", "llm", "recall@5", "citation acc", "refusal acc", "p50 latency"]
    print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")

    if args.check_baseline:
        recall = min(r["recall"] for r in rows if r["mode"] == "hybrid_rerank")
        print(f"\nhybrid_rerank recall@5 = {recall:.3f}, baseline = {CFG['baseline_recall_at_5']}")
        sys.exit(int(recall < CFG["baseline_recall_at_5"]))


if __name__ == "__main__":
    main()

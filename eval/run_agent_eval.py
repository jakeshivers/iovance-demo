"""Score the gap-assessor agent on scenarios with expected verdicts and cited sections."""
import json
import statistics
import time
from pathlib import Path

from run_eval import CITE, matches  # also puts the repo root on sys.path

from rag.agent import assess  # noqa: E402


def hit(exp: dict, findings: list[dict]) -> bool:
    """An expected finding is hit if some finding has its verdict and cites one of its sections."""
    return any(f["verdict"] == exp["verdict"] and any(matches(s, d, sec) for s in exp["sections"]
               for c in f["citations"] for d, sec in CITE.findall(c)) for f in findings)


def main():
    scenarios = [json.loads(l) for l in open(Path(__file__).parent / "agent_scenarios.jsonl")]
    rows, hits, total, unverified, cites, lat = [], 0, 0, 0, 0, []
    for i, s in enumerate(scenarios, 1):
        t = time.perf_counter()
        findings = assess(s["description"])
        lat.append(time.perf_counter() - t)
        got = [hit(e, findings) for e in s["expected"]]
        bad = sum(len(f["unverified"]) for f in findings)
        hits, total = hits + sum(got), total + len(got)
        unverified, cites = unverified + bad, cites + sum(len(f["citations"]) for f in findings)
        rows.append(f"| {i} | {s['description'][:60]}… | {sum(got)}/{len(got)} | "
                    f"{', '.join(f['verdict'] for f in findings)} | {bad} | {lat[-1]:.0f}s |")
    print("| # | scenario | expected hit | agent verdicts | unverified cites | latency |\n|---|---|---|---|---|---|")
    print("\n".join(rows))
    print(f"\n**finding recall {100 * hits / total:.0f}% ({hits}/{total}) · unverified citations {unverified}/{cites}"
          f" · p50 latency {statistics.median(lat):.0f}s**")


if __name__ == "__main__":
    main()

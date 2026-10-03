"""Compliance gap assessor: raw Anthropic tool-use loop over the regulatory search tool."""
import sys

from rag.generate import log
from rag.guard import GUARD_RULES, redact, wrap
from rag.interfaces import AnthropicLLM
from rag.retrieve import cite, search

MAX_TURNS = 10
SYSTEM = f"""You are a GxP computerized-systems compliance assessor.
Given a description of a system or SOP:
1. Split it into distinct practices or claims.
2. For each one, call search_regulatory_docs with a focused query. Refine and search again if results are off-topic.
3. Judge each claim against the retrieved FDA guidance ONLY: compliant, gap, or unclear (guidance does not address it).
4. Call report_findings once with every finding. Citations must be copied exactly from a retrieved document's cite attribute.

{GUARD_RULES}"""

TOOLS = [
    {"name": "search_regulatory_docs",
     "description": "Search FDA regulatory guidance. Returns top chunks, each with a [doc §section p.page] cite.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "report_findings",
     "description": "Submit the final assessment. Call exactly once, at the end.",
     "input_schema": {"type": "object", "required": ["findings"], "properties": {"findings": {"type": "array", "items": {
         "type": "object", "required": ["claim", "verdict", "severity", "citations", "remediation"],
         "properties": {
             "claim": {"type": "string"},
             "verdict": {"type": "string", "enum": ["compliant", "gap", "unclear"]},
             "severity": {"type": "string", "enum": ["high", "medium", "low", "none"]},
             "citations": {"type": "array", "items": {"type": "string"}},
             "remediation": {"type": "string"}}}}}}},
]


def assess(description: str) -> list[dict]:
    llm, seen = AnthropicLLM(), set()
    messages = [{"role": "user", "content": redact(description)}]
    for turn in range(MAX_TURNS):
        force = {"type": "tool", "name": "report_findings"} if turn == MAX_TURNS - 1 else {"type": "auto"}
        msg = llm.client.messages.create(model=llm.model, max_tokens=4096, system=SYSTEM,
                                         tools=TOOLS, tool_choice=force, messages=messages)
        messages.append({"role": "assistant", "content": msg.content})
        results = []
        for b in (b for b in msg.content if b.type == "tool_use"):
            if b.name == "report_findings":
                findings = b.input["findings"]
                for f in findings:  # output guardrail: every citation must come from a retrieved chunk
                    f["unverified"] = [c for c in f["citations"] if c not in seen]
                log.info("agent findings=%s", [(f["claim"], f["verdict"], f["citations"]) for f in findings])
                return findings
            hits = search(b.input["query"])
            seen.update(cite(h) for h in hits)
            log.info("agent search=%r cites=%s", b.input["query"], [cite(h) for h in hits])
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": "\n\n".join(wrap(cite(h), h["text"]) for h in hits)})
        if not results:
            messages.append({"role": "user", "content": "Call report_findings with your assessment."})
        else:
            messages.append({"role": "user", "content": results})
    raise RuntimeError("agent did not report findings")


def table(findings: list[dict]) -> str:
    rows = ["| claim | verdict | severity | citations | remediation |", "|---|---|---|---|---|"]
    for f in findings:
        cites = " ".join(f["citations"]) + (" ⚠ UNVERIFIED: " + " ".join(f["unverified"]) if f["unverified"] else "")
        rows.append(f"| {f['claim']} | {f['verdict']} | {f['severity']} | {cites} | {f['remediation']} |")
    return "\n".join(rows)


if __name__ == "__main__":
    print(table(assess(sys.argv[1])))

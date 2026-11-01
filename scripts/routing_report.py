#!/usr/bin/env python3
"""Summarize routing history: first-pass rate and cost per task shape and starting tier,
with suggested edits to references/routing.md.

Usage: routing_report.py [--min N]   (N = runs needed before suggesting, default 3)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HISTORY = SKILL / "history.jsonl"
LADDER = ["sonnet/low", "sonnet/medium", "sonnet/high", "opus/high"]


def main():
    min_n = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 3
    if not HISTORY.exists():
        print("No history yet. Outcomes are recorded as runs finish.")
        return
    rows = [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()]
    groups = defaultdict(list)
    for r in rows:
        groups[(r["shape"], r["first_tier"])].append(r)

    print(f"{'shape':<12} {'start tier':<15} {'n':>3} {'1st pass':>9} {'avg tries':>9} {'avg $':>7}  causes")
    suggestions = []
    for (shape, tier), rs in sorted(groups.items()):
        n = len(rs)
        fp = sum(r["first_pass"] for r in rs) / n
        tries = sum(r["attempts"] for r in rs) / n
        cost = sum(r["cost_usd"] for r in rs) / n
        causes = defaultdict(int)
        for r in rs:
            for c in r["causes"]:
                causes[c] += 1
        print(f"{shape:<12} {tier:<15} {n:>3} {fp:>8.0%} {tries:>9.1f} {cost:>7.2f}  {dict(causes) or '-'}")
        if n < min_n:
            continue
        if causes.get("brief", 0) >= n / 2:
            suggestions.append(f"{shape}: most failures were brief gaps. Tighten briefs (and trust the critic) before raising the tier.")
        elif fp < 0.6 and causes.get("capability", 0) and tier in LADDER[:-1]:
            suggestions.append(f"{shape}: first-pass {fp:.0%} at {tier} with capability failures. Consider starting at {LADDER[LADDER.index(tier) + 1]}.")
        elif fp == 1.0 and n >= 2 * min_n and tier in LADDER[1:]:
            suggestions.append(f"{shape}: {n}/{n} first-pass at {tier}. {LADDER[LADDER.index(tier) - 1]} might be enough; try it on one task.")
    print("\nSuggestions:" if suggestions else "\nNo suggestions yet.")
    for s in suggestions:
        print(f"- {s}")


if __name__ == "__main__":
    main()

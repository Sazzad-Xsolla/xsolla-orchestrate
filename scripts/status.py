#!/usr/bin/env python3
"""Build STATUS.md and dashboard.html for an orchestrate run, and print a check-in.

Usage: status.py <run_dir> [--oneline | --spent]
  --oneline  print a single heartbeat line instead of the full check-in
  --spent    print only the run's total spend in USD (used by the budget gate)
Files are rewritten in every mode except --spent.

Lines starting with "NOTIFY:" are new things the user should hear about now
(an approval, a blocker, drift, budget at 80%, the run finishing). Each is
printed once per run; send it as a push notification.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
PORT = os.environ.get("HEADROOM_PORT", "8787")


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def short_action(tool, root=""):
    inp = tool.get("input", {})
    detail = inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp.get("url") or ""
    if root:
        detail = str(detail).replace(root.rstrip("/") + "/", "")
    return f"{tool.get('name')}: {str(detail)[:90]}".rstrip(": ")


# $ per million tokens: (input, output, cache read). Cache writes are 1.25x input (5-minute)
# and 2x input (1-hour). Used only when a worker died without reporting its own cost
# (stop_worker.sh interrupts gracefully, so it normally reports). It is a LOWER BOUND:
# the log's per-message usage omits Claude Code's background calls and has partial output
# counts; calibrated at 23-94% of the real figure.
PRICES = {
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-fable-5-1": (10.00, 50.00, 0.25),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}


def estimate_cost(usages, model):
    price = next((p for m, p in PRICES.items() if model and model.startswith(m)), None)
    if not price:
        return None
    inp, out, read = price
    total = 0.0
    for u in usages:
        split = u.get("cache_creation") or {}
        w1h = split.get("ephemeral_1h_input_tokens", 0)
        w5m = split.get("ephemeral_5m_input_tokens", u.get("cache_creation_input_tokens", 0) - w1h)
        total += (u.get("input_tokens", 0) * inp + u.get("output_tokens", 0) * out
                  + u.get("cache_read_input_tokens", 0) * read + w5m * inp * 1.25 + w1h * inp * 2) / 1e6
    return total


def parse_log(path, root=""):
    out = {"turns": 0, "last_action": "", "last_text": "", "cost": None, "cost_estimated": False,
           "result": None, "denials": [], "model_seen": None, "blocked_hooks": 0}
    usages = {}  # one usage per API response; a response can span several assistant events
    if not Path(path).exists():
        return out
    for line in Path(path).read_text(errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        t = e.get("type")
        if t == "system" and e.get("subtype") == "init":
            out["model_seen"] = e.get("model")
        elif t == "assistant":
            out["turns"] += 1
            msg = e.get("message", {})
            if msg.get("usage"):
                usages[msg.get("id") or e.get("request_id") or len(usages)] = msg["usage"]
            for c in msg.get("content", []):
                if c.get("type") == "tool_use":
                    out["last_action"] = short_action(c, root)
                elif c.get("type") == "text" and c.get("text", "").strip():
                    out["last_text"] = c["text"].strip().splitlines()[-1][:200]
        elif t == "user":
            content = e.get("message", {}).get("content")
            for c in content if isinstance(content, list) else []:
                if c.get("type") == "tool_result" and "BLOCKED by orchestrator" in str(c.get("content")):
                    out["blocked_hooks"] += 1
        elif t == "result":
            out["cost"] = e.get("total_cost_usd")
            out["result"] = {"subtype": e.get("subtype"), "is_error": e.get("is_error"),
                             "text": (e.get("result") or "")[:300]}
            out["denials"] = [
                (d.get("tool_input") or {}).get("command") or d.get("tool_name")
                for d in e.get("permission_denials", [])
            ]
    if out["cost"] is None and usages:
        out["cost"] = estimate_cost(list(usages.values()), out["model_seen"])
        out["cost_estimated"] = out["cost"] is not None
    return out


def task_cost_detail(wdir):
    """(spend for one task across every attempt plus its brief critique, any part estimated?)"""
    wdir = Path(wdir)
    total, estimated = 0.0, False
    for p in [wdir / "log.jsonl", *sorted(wdir.glob("log.attempt*.jsonl"))]:
        log = parse_log(p)
        total += log["cost"] or 0
        estimated = estimated or log["cost_estimated"]
    crit = read_json(wdir / "critique.json", {})
    total += crit.get("total_cost_usd") or 0
    return total, estimated


def task_cost(wdir):
    return task_cost_detail(wdir)[0]


def report_status(path):
    if not Path(path).exists():
        return None
    for line in Path(path).read_text(errors="replace").splitlines():
        if line.lower().startswith("status:"):
            return line.split(":", 1)[1].strip().split()[0].strip("|")
    return "unknown"


def headroom_stats():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/stats", timeout=3) as r:
            return json.load(r)
    except Exception:
        return None


def drift(plan):
    project = plan.get("project_dir")
    try:
        out = subprocess.run(["git", "-C", project, "status", "--porcelain"],
                             capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    if out.returncode != 0:
        return []
    allowed = [w for t in plan.get("tasks", []) for w in t.get("writes", [])]
    preexisting = set(plan.get("git_dirty_at_start", []))
    found = []
    for line in out.stdout.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        if path.startswith(".xsolla-orchestrator/") or path in preexisting:
            continue
        if any(path == w or (w.endswith("/") and path.startswith(w)) for w in allowed):
            continue
        found.append(path)
    return found


def fmt_secs(s):
    s = int(s)
    return f"{s // 60}m{s % 60:02d}s" if s >= 60 else f"{s}s"


def collect(run):
    from memory import snapshot
    plan = read_json(run / "plan.json", {})
    root = plan.get("project_dir", "")
    stats = headroom_stats()
    per_project = (stats or {}).get("savings", {}).get("per_project", {})
    now = time.time()
    workers = []
    for t in plan.get("tasks", []):
        w = run / "workers" / t["id"]
        meta = read_json(w / "meta.json", {})
        log = parse_log(w / "log.jsonl", root)
        rstat = report_status(w / "report.md")
        alive = bool(meta.get("pid")) and "ended_at" not in meta and pid_alive(meta["pid"])
        state = t.get("state", "planned")
        if state == "running" and meta.get("runtime") == "headless" and not alive and "ended_at" in meta:
            state = "awaiting review"
        if state == "running" and meta.get("runtime") == "fork" and rstat:
            state = "awaiting review"
        result = log["result"] or {}
        if result.get("subtype", "").startswith("error"):
            log["last_text"] = f"ended with {result['subtype']}"
        started, ended = meta.get("started_at"), meta.get("ended_at")
        elapsed = (ended or now) - started if started else None
        tag = f"xsolla-orch-{plan.get('run_id')}-{t['id']}"
        saved = sum(v.get("tokens_saved", 0) for k, v in per_project.items() if k.startswith(tag))
        saved_usd = sum(v.get("compression_savings_usd", 0) for k, v in per_project.items() if k.startswith(tag))
        accepts = t.get("accept_results", [])
        crit = (w / "critique.md").read_text() if (w / "critique.md").exists() else ""
        cost, cost_est = task_cost_detail(w)
        causes = [h.get("cause") for h in t.get("routing_history", [])]
        counted = [c for c in causes if c not in ("environment", "budget", "resume")]
        dog = read_json(w / "watchdog.json", {})
        if state == "paused" and dog.get("signals"):
            log["last_text"] = "Paused by watchdog: " + dog["signals"][0]["detail"]
        workers.append({
            "id": t["id"], "title": t.get("title", ""), "state": state, "shape": t.get("shape", ""),
            "runtime": t.get("runtime", "headless"), "model": t.get("model"),
            "effort": t.get("effort"), "attempt": t.get("attempt", 1),
            "budget_usd": t.get("budget_usd"),
            "routing_reason": t.get("routing_reason", ""), "specialist": t.get("specialist"),
            "cost_usd": round(cost, 4) if meta and meta.get("runtime") != "fork" else None,
            "cost_estimated": cost_est,
            "turns": log["turns"], "last_action": log["last_action"],
            "last_text": log["last_text"], "report_status": rstat,
            "denials": log["denials"], "blocked_writes": log["blocked_hooks"], "routed": meta.get("routed"),
            "resumed": meta.get("resumed_from") not in (None, "-"),
            "model_seen": log["model_seen"], "exit_code": meta.get("exit_code"),
            "killed": bool(meta.get("killed")), "kill_reason": meta.get("kill_reason"),
            "elapsed": fmt_secs(elapsed) if elapsed is not None else "",
            "depends_on": t.get("depends_on", []), "writes": t.get("writes", []),
            "saved_tokens": saved, "saved_usd": round(saved_usd, 3),
            "accept": (accepts[-1] if accepts else None),
            "critic": ("needs-fixes" if "VERDICT: needs-fixes" in crit else "clear" if "VERDICT: clear" in crit else None),
            "causes": counted, "counted_attempt": len(counted) + 1,
            "extensions": causes.count("budget"), "resumes": causes.count("resume"),
            "watchdog": (dog.get("signals") or [{}])[0].get("signal") if state == "paused" else None,
        })
    total = len(workers) or 1
    verified = sum(1 for w in workers if w["state"] == "verified")
    spend = round(sum(w["cost_usd"] or 0 for w in workers), 2)
    budget = plan.get("run_budget_usd")
    from field_team import enrich
    return enrich(run, {
        "title": plan.get("title") or plan.get("run_id", "Run"),
        "run_id": plan.get("run_id"), "goal": plan.get("goal", ""), "theme": plan.get("dashboard_theme"),
        "definition_of_done": plan.get("definition_of_done", []),
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "progress": round(100 * verified / total), "all_done": bool(workers) and verified == len(workers),
        "workers": workers,
        "demo": bool(plan.get("demo")), "mode": "Demonstration" if plan.get("demo") else "Live run",
        "messages": read_json(run / "coordination" / "messages.json", []),
        "memory": snapshot(root),
        "approvals": [a for a in plan.get("approvals", []) if a.get("status") == "pending"],
        "approvals_done": [a for a in plan.get("approvals", []) if a.get("status") != "pending"],
        "blockers": [w for w in workers if w["state"] in ("blocked", "paused") or w["report_status"] == "blocked"],
        "drift": drift(plan),
        "headroom": {"available": stats is not None,
                     "tokens_saved": sum(w["saved_tokens"] for w in workers),
                     "usd_saved": round(sum(w["saved_usd"] for w in workers), 3)},
        "spend_usd": spend, "run_budget_usd": budget,
        "budget_pct": round(100 * spend / budget) if budget else None,
        "log": plan.get("log", [])[-8:],
        "status_path": str(run / "STATUS.md"),
    }, plan)


def render_md(d):
    L = [f"# {d['title']}: status", "",
         f"_Updated {d['updated']} · run `{d['run_id']}` · {d['progress']}% verified_", "",
         f"**Goal:** {d['goal']}", ""]
    needs = []
    for a in d["approvals"]:
        needs.append(f"- **Approve {a.get('kind')}** → {a.get('target')} (from {a.get('from_task')}, id `{a.get('id')}`)\n"
                     f"  ```\n  {a.get('text', '').strip()}\n  ```")
    for b in d["blockers"]:
        if b["state"] == "paused":
            needs.append(f"- **Paused:** {b['id']} {b['title']}. {b['last_text']}. Continue with guidance, step up, or stop?")
        else:
            needs.append(f"- **Blocked:** {b['id']} {b['title']}. See `workers/{b['id']}/report.md`")
    if d["drift"]:
        needs.append("- **Drift:** files changed outside every task's write list: " + ", ".join(f"`{p}`" for p in d["drift"]))
    if d["budget_pct"] is not None and d["budget_pct"] >= 80:
        needs.append(f"- **Budget:** ${d['spend_usd']:.2f} of ${d['run_budget_usd']} used ({d['budget_pct']}%)")
    L += ["## Needs you", *(needs or ["- Nothing right now."]), ""]
    L += ["## Workers", "",
          "| id | task | model · effort | runtime | state | attempt | accept | cost / checkpoint | saved | elapsed | last action |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for w in d["workers"]:
        cost = (("≥$" if w["cost_estimated"] else "$") + f"{w['cost_usd']:.2f}") if w["cost_usd"] is not None else "–"
        cap = f"${w['budget_usd']}" if w["budget_usd"] is not None else "–"
        routed = "" if w["runtime"] == "fork" else (" (headroom)" if w["routed"] else " (unwrapped)" if w["routed"] is False else "")
        acc = "–" if not w["accept"] else ("pass" if w["accept"]["passed"] else "FAIL")
        tries = f"{w['counted_attempt']}" + (f" ({', '.join(w['causes'])})" if w["causes"] else "")
        tries += f", extended ×{w['extensions']}" if w["extensions"] else ""
        L.append(f"| {w['id']} | {w['title']} | {w['model']} · {w['effort']} | {w['runtime']}{routed} | {w['state']} | "
                 f"{tries} | {acc} | {cost} / {cap} | {w['saved_tokens']:,} tok | {w['elapsed']} | "
                 f"{(w['last_action'] or '').replace('|', '/')} |")
    L += ["", "## Definition of done"]
    for c in d["definition_of_done"]:
        L.append(f"- [{'x' if c.get('met') else ' '}] {c.get('text')}" + (f": {c['evidence']}" if c.get("evidence") else ""))
    h = d["headroom"]
    budget = f" of ${d['run_budget_usd']} budget ({d['budget_pct']}%)" if d["run_budget_usd"] else ""
    L += ["", "## Spend and savings",
          f"- Worker spend: ${d['spend_usd']:.2f}{budget}",
          (f"- Headroom savings for this run's workers: {h['tokens_saved']:,} tokens, ${h['usd_saved']:.3f}"
           if h["available"] else "- Headroom: proxy not reachable")]
    if d["log"]:
        L += ["", "## Recent decisions", *[f"- {e.get('at', '')}: {e.get('note', '')}" for e in d["log"]]]
    return "\n".join(L) + "\n"


THEMES = {"xsolla": SKILL / "prototypes" / "xsolla-run.html"}


def render_html(d, theme=None):
    """Fill a dashboard theme with run data. Theme: argument, else plan.json "dashboard_theme",
    else ORCH_THEME, else xsolla."""
    name = theme or d.get("theme") or os.environ.get("ORCH_THEME") or "xsolla"
    tpl = THEMES.get(name, THEMES["xsolla"]).read_text()
    data = json.dumps(d).replace("</", "<\\/")
    title = (d["title"] or "Run").replace("<", "").replace("&", "and")
    return tpl.replace("__TITLE__", title).replace('"__DATA__"', data)


def notifications(run, d):
    """New attention items since the last call, each reported once per run."""
    seen_path = run / ".notified.json"
    seen = set(read_json(seen_path, []))
    items = {}
    for a in d["approvals"]:
        items[f"approval:{a.get('id')}"] = f"{d['title']}: approve {a.get('kind')} -> {a.get('target')} ({a.get('id')})"
    for b in d["blockers"]:
        if b["state"] == "paused":
            items[f"paused:{b['id']}:{b['attempt']}"] = f"{d['title']}: {b['id']} paused. {b['last_text']}"
        else:
            items[f"blocked:{b['id']}"] = f"{d['title']}: {b['id']} is blocked and needs your answer"
    if d["drift"]:
        items["drift:" + ",".join(sorted(d["drift"]))] = f"{d['title']}: unexpected file changes: {', '.join(d['drift'][:3])}"
    if d["budget_pct"] is not None and d["budget_pct"] >= 80:
        items["budget80"] = f"{d['title']}: ${d['spend_usd']:.2f} of ${d['run_budget_usd']} budget used"
    if d["all_done"]:
        items["done"] = f"{d['title']}: all {len(d['workers'])} tasks verified, ready for close-out"
    new = [msg for k, msg in items.items() if k not in seen]
    seen_path.write_text(json.dumps(sorted(seen | set(items))))
    return new


def checkin(d):
    running = [w for w in d["workers"] if w["state"] == "running"]
    review = [w for w in d["workers"] if w["state"] == "awaiting review"]
    parts = [f"{d['progress']}% verified", f"${d['spend_usd']:.2f}" + (f"/{d['run_budget_usd']}" if d["run_budget_usd"] else "")]
    if running:
        parts.append("running: " + ", ".join(f"{w['id']} {w['model']}/{w['effort']} {w['elapsed']}" for w in running))
    if review:
        parts.append("awaiting review: " + ", ".join(w["id"] for w in review))
    if d["blockers"]:
        parts.append("blocked: " + ", ".join(w["id"] for w in d["blockers"]))
    if d["approvals"]:
        parts.append(f"{len(d['approvals'])} approval(s) pending")
    if d["drift"]:
        parts.append(f"DRIFT: {len(d['drift'])} unexpected file(s)")
    return " | ".join(parts)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = Path(sys.argv[1]).resolve()
    if "--spent" in sys.argv:
        plan = read_json(run / "plan.json", {})
        print(round(sum(task_cost(run / "workers" / t["id"]) for t in plan.get("tasks", [])), 4))
        return
    d = collect(run)
    (run / "STATUS.md").write_text(render_md(d))
    (run / "dashboard.html").write_text(render_html(d))
    # Brand fonts beside the static page, so it renders opened from disk and the
    # artifact copy can publish them as supporting files.
    fonts = run / "fonts"
    if not fonts.exists():
        fonts.mkdir()
        for f in (SKILL / "assets" / "fonts").glob("*.woff2"):
            (fonts / f.name).write_bytes(f.read_bytes())
    new = notifications(run, d)
    if "--oneline" in sys.argv:
        print("heartbeat: " + checkin(d), flush=True)
    else:
        print(checkin(d))
        for w in d["workers"]:
            if w["state"] in ("running", "awaiting review", "blocked", "failed"):
                extra = f" | denied: {', '.join(map(str, w['denials']))}" if w["denials"] else ""
                extra += f" | {w['blocked_writes']} blocked write(s)" if w["blocked_writes"] else ""
                print(f"- {w['id']} [{w['state']}] {w['last_text'] or w['last_action']}{extra}")
        print(f"STATUS.md: {d['status_path']}")
    for msg in new:
        print(f"NOTIFY: {msg}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Inspect local prerequisites without starting workers or making AI API requests."""
import json
import shutil
import subprocess
import sys
from urllib.request import urlopen

REQUIRED_FLAGS = ("--effort", "--model", "--settings", "--strict-mcp-config", "--max-budget-usd",
                  "--exclude-dynamic-system-prompt-sections", "--output-format", "--resume")


def check():
    checks = [{"name": "Python 3.9+", "ok": sys.version_info >= (3, 9), "required": True}]
    for command in ("bash", "curl", "git", "claude"):
        checks.append({"name": command, "ok": bool(shutil.which(command)), "required": True})
    if shutil.which("claude"):
        help_text = subprocess.run(["claude", "--help"], capture_output=True, text=True, timeout=20).stdout
        checks.append({"name": "Claude worker flags", "ok": all(flag in help_text for flag in REQUIRED_FLAGS), "required": True})
    try:
        with urlopen("http://127.0.0.1:8787/health", timeout=1) as response:
            proxy = response.status == 200
    except OSError:
        proxy = False
    checks.append({"name": "Optional headroom proxy", "ok": proxy, "required": False})
    return {"checks": checks, "ready": all(c["ok"] for c in checks if c["required"]),
            "note": "CLI flags were checked locally. Authentication and model access require a real pilot run. Set ORCH_ALLOW_UNWRAPPED=1 to run without the optional proxy."}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready"] else 1)

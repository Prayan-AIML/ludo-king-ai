"""
One command to refresh all web data from real models.

It loads API keys from ../.env.local (or ../.env), then:
  1. runs the Track A benchmark   -> ../leaderboard.json
  2. exports the watchable set     -> ../decisions.json (with model picks)

Any provider without a key is simply skipped / left as "awaiting".

Usage:  cd benchmark && python3 update.py
"""
from __future__ import annotations

import os


def load_env():
    root = os.path.join(os.path.dirname(__file__), "..")
    for name in (".env.local", ".env"):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        print(f"Loaded API keys from {name}")
        return True
    print("No .env.local / .env found — running baselines only.")
    return False


if __name__ == "__main__":
    load_env()
    import run
    import export_decisions
    print("\n=== 1/2: benchmark -> leaderboard.json ===")
    run.run()
    print("\n=== 2/2: watchable decisions -> decisions.json ===")
    export_decisions.export(40)
    print("\nDone. Commit & push leaderboard.json + decisions.json to update the site.")

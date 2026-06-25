"""
Export a sample of decision positions to ../decisions.json so the web viewer
(watch.html) can render them on a board and let humans WATCH each decider
choose a move.

Each item carries the raw token positions, the die, the legal moves, the
oracle's best move(s), and a `picks` map of {decider_label: chosen_move_id}.
Today the deciders are the keyless baselines (Oracle + Random); when real
models run, add their picks to the same map and the viewer shows them too.

Usage: python3 export_decisions.py [n=40]
"""
from __future__ import annotations

import json
import os
import random
import sys

from ludo import distinct_legal_moves
from oracle import rank_moves, best_move_ids
import positions as pos_mod


def export(n=40, seed=42):
    src = pos_mod.generate(n_positions=n, seed=seed)
    rng = random.Random(seed)
    items = []
    for p in src:
        state, player, die = p["state"], p["player"], p["die"]
        moves = distinct_legal_moves(state, player, die)
        _, values, best = rank_moves(state, player, die)
        best_ids = sorted(best_move_ids(moves, values, best))
        valid_ids = [m["id"] for m in moves]

        items.append({
            "id": p["id"],
            "die": die,
            "player": player,
            "tokens": state,
            "moves": [{
                "id": m["id"],
                "token": m["token"],
                "from_rel": m["from_rel"],
                "to_rel": m["to_rel"],
                "captures": [opp for opp, _ in m["captures"]],
            } for m in moves],
            "oracle_best": best_ids,
            "picks": {
                "Oracle (ceiling)": min(best_ids),
                "Random (floor)": rng.choice(valid_ids),
                # Real models get added here when they run, e.g.:
                # "GPT-5.5": 3, "Claude Opus 4.8": 1, "Gemini 3.1 Pro": 2
            },
        })

    deciders = [
        {"label": "Oracle (ceiling)", "color": "#34b27b"},
        {"label": "Random (floor)",   "color": "#9aa3b2"},
    ]
    out = {"n_positions": len(items), "deciders": deciders, "items": items}
    path = os.path.join(os.path.dirname(__file__), "..", "decisions.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"Wrote {len(items)} watchable decisions -> {os.path.abspath(path)}")


if __name__ == "__main__":
    export(int(sys.argv[1]) if len(sys.argv) > 1 else 40)

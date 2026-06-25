"""
Export a sample of decision positions to ../decisions.json so the web viewer
(watch.html) can render them on a board and let humans WATCH each strategy
choose a move — with the expert's SCORE and plain-English REASONS for every
move, so it's clear why one move beats another.

Each item carries the token positions, the die, the legal moves (each with a
heuristic `value` score and human `factors`), the oracle's best move(s), and a
`picks` map of {strategy_label: chosen_move_id}.

Usage: python3 export_decisions.py [n=40]
"""
from __future__ import annotations

import json
import os
import random
import sys

from ludo import (distinct_legal_moves, apply_move, abs_square, SAFE,
                  TRACK_LEN, FINISH)
from oracle import rank_moves, best_move_ids
import positions as pos_mod


def move_factors(state, player, m):
    """Plain-English reasons a move is good or risky."""
    fac = []
    caps = sorted({opp for opp, _ in m["captures"]})
    if m["from_rel"] == -1:
        fac.append("frees a token from base")
    if caps:
        fac.append("captures " + ", ".join(caps))
    if m["to_rel"] == FINISH:
        fac.append("finishes a token (reaches home)")
    elif m["to_rel"] >= 51:
        fac.append("enters the safe home stretch")
    elif m["to_rel"] <= 50 and abs_square(player, m["to_rel"]) in SAFE:
        fac.append("lands on a safe square")

    ns = apply_move(state, player, m)
    rel = ns[player][m["token"]]
    if 0 <= rel <= 50 and abs_square(player, rel) not in SAFE:
        a = abs_square(player, rel)
        exposed = False
        for p in ns:
            if p == player:
                continue
            for orel in ns[p]:
                if 0 <= orel <= 50 and 1 <= (a - abs_square(p, orel)) % TRACK_LEN <= 6:
                    exposed = True
                    break
            if exposed:
                break
        if exposed:
            fac.append("leaves that token exposed to capture")

    if not fac:
        adv = m["to_rel"] - (0 if m["from_rel"] == -1 else m["from_rel"])
        fac.append(f"advances a token {adv} square" + ("s" if adv != 1 else ""))
    return fac


def export(n=40, seed=42):
    src = pos_mod.generate(n_positions=n, seed=seed)
    rng = random.Random(seed)
    items = []
    for p in src:
        state, player, die = p["state"], p["player"], p["die"]
        moves, values, best = rank_moves(state, player, die)
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
                "value": round(v, 1),
                "factors": move_factors(state, player, m),
            } for m, v in zip(moves, values)],
            "oracle_best": best_ids,
            "picks": {
                "Oracle (ceiling)": min(best_ids),
                "Random (floor)": rng.choice(valid_ids),
                # Real models get added here when they run.
            },
        })

    deciders = [
        {"label": "Oracle (ceiling)", "short": "Oracle", "color": "#1d8a5b",
         "blurb": "the expert — always picks the highest-scoring move"},
        {"label": "Random (floor)", "short": "Random", "color": "#8a93a3",
         "blurb": "picks a legal move blindly, ignoring the board"},
    ]
    out = {"n_positions": len(items), "deciders": deciders, "items": items}
    path = os.path.join(os.path.dirname(__file__), "..", "decisions.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"Wrote {len(items)} decisions (with scores + reasons) -> {os.path.abspath(path)}")


if __name__ == "__main__":
    export(int(sys.argv[1]) if len(sys.argv) > 1 else 40)

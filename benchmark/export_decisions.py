"""
Export a sample of decision positions to ../decisions.json for the web viewer
(watch.html). It writes:
  - the board state, die, legal moves (each with a heuristic score + reasons),
  - the oracle's best move,
  - and a `picks` map of {strategy: chosen_move_id}.

Deciders are organised into GROUPS so the viewer can toggle between them:
  group 1 = "Oracle vs Random"  (baselines, always populated, no key needed)
  group 2 = "AI models"          (GPT / Gemini / Claude — populated only if the
                                  matching API key is set; otherwise left empty
                                  and the viewer shows "awaiting key")

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
from prompt import SYSTEM, build_user
from parse import extract_move_id
from providers import make_provider, ProviderError
import positions as pos_mod
import config


def move_factors(state, player, m):
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
        exposed = any(
            0 <= orel <= 50 and 1 <= (a - abs_square(p, orel)) % TRACK_LEN <= 6
            for p in ns if p != player for orel in ns[p]
        )
        if exposed:
            fac.append("leaves that token exposed to capture")

    if not fac:
        adv = m["to_rel"] - (0 if m["from_rel"] == -1 else m["from_rel"])
        fac.append(f"advances a token {adv} square" + ("s" if adv != 1 else ""))
    return fac


def export(n=40, seed=42):
    pool = pos_mod.generate(n_positions=n * 6, seed=seed)
    random.Random(seed + 7).shuffle(pool)
    src = pool[:n]
    rng = random.Random(seed)

    # set up model providers; a missing key just disables that model
    model_entries = [e for e in config.MODELS
                     if e["kind"] in ("openai", "anthropic", "google")]
    provs = {e["label"]: make_provider(e["kind"], e["model"]) for e in model_entries}
    disabled = set()

    items = []
    for p in src:
        state, player, die = p["state"], p["player"], p["die"]
        moves, values, best = rank_moves(state, player, die)
        best_ids = sorted(best_move_ids(moves, values, best))
        valid_ids = [m["id"] for m in moves]
        user, _ = build_user(p)

        picks = {
            "Oracle (ceiling)": min(best_ids),
            "Random (floor)": rng.choice(valid_ids),
        }
        for e in model_entries:
            label = e["label"]
            if label in disabled:
                continue
            try:
                res = provs[label].decide(SYSTEM, user)
            except ProviderError:
                disabled.add(label)
                print(f"  [skip] {label}: no API key — left as 'awaiting'")
                continue
            except Exception as ex:
                print(f"  [warn] {label} errored on a position: {ex}")
                continue
            pid = extract_move_id(res.text, valid_ids)
            if pid is not None:
                picks[label] = pid

        items.append({
            "id": p["id"], "die": die, "player": player, "tokens": state,
            "moves": [{
                "id": m["id"], "token": m["token"], "from_rel": m["from_rel"],
                "to_rel": m["to_rel"], "captures": [o for o, _ in m["captures"]],
                "value": round(v, 1), "factors": move_factors(state, player, m),
            } for m, v in zip(moves, values)],
            "oracle_best": best_ids,
            "picks": picks,
        })

    base = [
        {"label": "Oracle (ceiling)", "short": "Oracle", "color": "#1d8a5b",
         "blurb": "the expert — always picks the highest-scoring move"},
        {"label": "Random (floor)", "short": "Random", "color": "#8a93a3",
         "blurb": "picks a legal move blindly, ignoring the board"},
    ]
    models = [{"label": e["label"], "short": e["label"],
               "color": config.COLORS.get(e["label"], "#3d8bd4"),
               "blurb": "AI model under test"} for e in model_entries]
    groups = [
        {"name": "Oracle vs Random", "deciders": base},
        {"name": "AI models", "deciders": models},
    ]

    out = {"n_positions": len(items), "groups": groups, "items": items}
    path = os.path.join(os.path.dirname(__file__), "..", "decisions.json")
    with open(path, "w") as f:
        json.dump(out, f)
    ran = [m["label"] for m in models if m["label"] not in disabled]
    print(f"Wrote {len(items)} decisions -> {os.path.abspath(path)}")
    print("Model picks populated for:", ", ".join(ran) if ran else "(none — no keys)")


if __name__ == "__main__":
    export(int(sys.argv[1]) if len(sys.argv) > 1 else 40)

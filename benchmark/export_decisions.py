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
        return True
    return False

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


def export(n=40, seed=42, retry_model=None):
    pool = pos_mod.generate(n_positions=n * 6, seed=seed)
    random.Random(seed + 7).shuffle(pool)
    src = pool[:n]
    rng = random.Random(seed)

    # set up model providers; a missing key just disables that model
    model_entries = [e for e in config.MODELS
                     if e["kind"] in ("openai", "anthropic", "google")]
    if retry_model:
        model_entries = [e for e in model_entries if e["label"] == retry_model]
    provs = {e["label"]: make_provider(e["kind"], e["model"]) for e in model_entries}
    disabled = set()

    # if retrying, load existing decisions and only re-query failed positions
    existing_items_by_id = {}
    if retry_model:
        path = os.path.join(os.path.dirname(__file__), "..", "decisions.json")
        try:
            with open(path) as f:
                existing = json.load(f)
            existing_items_by_id = {item["id"]: item for item in existing["items"]}
            # only re-query positions where this model failed
            src = [p for p in src if p["id"] not in existing_items_by_id or retry_model not in existing_items_by_id[p["id"]]["picks"]]
            if not src:
                print(f"All {n} positions already have {retry_model} picks.")
                return
        except (FileNotFoundError, IndexError, KeyError):
            pass

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

    # if retrying a model, merge new picks into existing
    if retry_model:
        with open(path) as f:
            existing = json.load(f)
        new_ids = {item["id"] for item in items}
        for new_item in items:
            idx = next((i for i, e in enumerate(existing["items"]) if e["id"] == new_item["id"]), None)
            if idx is not None:
                existing["items"][idx]["picks"].update(new_item["picks"])
        with open(path, "w") as f:
            json.dump(existing, f)
        print(f"Wrote {len(items)} retried decisions -> {os.path.abspath(path)}")
    else:
        with open(path, "w") as f:
            json.dump(out, f)
        print(f"Wrote {len(items)} decisions -> {os.path.abspath(path)}")

    ran = [m["label"] for m in models if m["label"] not in disabled]
    print("Model picks populated for:", ", ".join(ran) if ran else "(none — no keys)")


if __name__ == "__main__":
    load_env()
    n = 40
    retry_model = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            retry_model = args[i + 1]
            i += 2
        elif args[i].isdigit():
            n = int(args[i])
            i += 1
        else:
            i += 1
    export(n, retry_model=retry_model)

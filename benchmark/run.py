"""
Track A — Decision Quality benchmark runner.

For each model, for each fixed decision position:
  build prompt -> get the model's chosen move -> compare to the oracle.

Outputs:
  results.csv      one row per (model, position) decision
  summary.json     aggregate metrics per model
and prints a leaderboard.

Run the baselines today (no keys):   python run.py
Add real models by setting keys:     OPENAI_API_KEY=... ANTHROPIC_API_KEY=... GOOGLE_API_KEY=... python run.py
"""
from __future__ import annotations

import csv
import json
import os
import random

import config
import positions as pos_mod
from prompt import SYSTEM, build_user
from parse import extract_move_id
from oracle import rank_moves, best_move_ids
from providers import make_provider, ProviderError


def get_positions():
    path = "positions.jsonl"
    if not os.path.exists(path):
        print(f"Generating {config.N_POSITIONS} positions (seed={config.SEED})...")
        pos = pos_mod.generate(n_positions=config.N_POSITIONS, seed=config.SEED)
        pos_mod.save(pos, path)
    return pos_mod.load(path)


def decide_for_model(entry, position, ranked, rng):
    """Return (chosen_id, latency, usage, status) for one model on one position."""
    moves, values, best = ranked
    valid_ids = [m["id"] for m in moves]
    kind = entry["kind"]

    if kind == "random":
        return rng.choice(valid_ids), 0.0, None, "ok"
    if kind == "oracle":
        best_ids = best_move_ids(moves, values, best)
        return min(best_ids), 0.0, None, "ok"

    # real provider
    user, _ = build_user(position)
    try:
        res = entry["_provider"].decide(SYSTEM, user)
    except ProviderError:
        raise                      # bubble up: skip whole model
    except Exception as e:         # network/API error on this position
        return None, 0.0, None, f"error:{type(e).__name__}"
    chosen = extract_move_id(res.text, valid_ids)
    if chosen is None:
        return None, res.latency_s, res.usage, "illegal"
    return chosen, res.latency_s, res.usage, "ok"


def value_of(moves, values, chosen_id):
    for m, v in zip(moves, values):
        if m["id"] == chosen_id:
            return v
    return None


def run():
    posns = get_positions()
    print(f"Loaded {len(posns)} decision positions.\n")

    # Pre-compute oracle ranking once per position (shared across all models).
    ranks = []
    for p in posns:
        ranks.append(rank_moves(p["state"], p["player"], p["die"]))

    rows = []
    summaries = []
    pending_labels = []

    for entry in config.MODELS:
        label, kind = entry["label"], entry["kind"]
        if kind in ("openai", "anthropic", "google"):
            entry["_provider"] = make_provider(kind, entry["model"])
        rng = random.Random(config.SEED)   # reproducible random baseline

        n = agree = illegal = error = 0
        regret_sum = lat_sum = 0.0
        tok_in = tok_out = 0
        skipped = False

        for p, ranked in zip(posns, ranks):
            moves, values, best = ranked
            worst = min(values)
            span = (best - worst) or 1.0
            try:
                chosen, lat, usage, status = decide_for_model(entry, p, ranked, rng)
            except ProviderError as e:
                print(f"  [skip] {label}: {e}")
                skipped = True
                break

            n += 1
            lat_sum += lat
            if usage:
                tok_in += usage.get("input") or 0
                tok_out += usage.get("output") or 0

            if status == "ok":
                best_ids = best_move_ids(moves, values, best)
                if chosen in best_ids:
                    agree += 1
                regret_sum += (best - value_of(moves, values, chosen)) / span
            else:
                if status == "illegal":
                    illegal += 1
                else:
                    error += 1
                regret_sum += 1.0       # worst-case regret for an unusable move

            rows.append({
                "model": label, "position": p["id"], "die": p["die"],
                "n_options": len(moves), "chosen": chosen, "status": status,
                "latency_s": round(lat, 3),
            })

        if skipped or n == 0:
            if kind in ("openai", "anthropic", "google"):
                pending_labels.append(label)
            continue

        summaries.append({
            "model": label,
            "decisions": n,
            "optimal_move_pct": round(100 * agree / n, 1),
            "mean_norm_regret": round(regret_sum / n, 3),
            "illegal_pct": round(100 * illegal / n, 1),
            "error_pct": round(100 * error / n, 1),
            "mean_latency_s": round(lat_sum / n, 3),
            "tokens_in": tok_in, "tokens_out": tok_out,
        })

    _write(rows, summaries)
    _write_web_leaderboard(summaries, pending_labels, len(posns))
    _print_leaderboard(summaries)


def _write(rows, summaries):
    with open("results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model", "position", "die",
                                          "n_options", "chosen", "status",
                                          "latency_s"])
        w.writeheader()
        w.writerows(rows)
    with open("summary.json", "w") as f:
        json.dump(summaries, f, indent=2)
    print("\nWrote results.csv and summary.json")


def _write_web_leaderboard(summaries, pending_labels, n_positions):
    """Write ../leaderboard.json so the web page (benchmark.html) shows results."""
    import datetime
    by_label = {s["model"]: s for s in summaries}
    rows = []
    for entry in config.MODELS:
        label = entry["label"]
        row = {"label": label, "color": config.COLORS.get(label, "#9aa3b2")}
        if label in config.NOTES:
            row["note"] = config.NOTES[label]
        if label in by_label:
            row["optimal_pct"] = by_label[label]["optimal_move_pct"]
            row["state"] = "done"
        elif label in pending_labels:
            row["state"] = "pending"
        else:
            continue
        rows.append(row)

    out = {"updated": str(datetime.date.today()),
           "n_positions": n_positions, "rows": rows}
    path = os.path.join(os.path.dirname(__file__), "..", "leaderboard.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote web leaderboard -> {os.path.abspath(path)}")


def _print_leaderboard(summaries):
    if not summaries:
        print("\nNo models ran. Set at least one API key, or rely on baselines.")
        return
    order = sorted(summaries, key=lambda s: (-s["optimal_move_pct"],
                                             s["mean_norm_regret"]))
    print("\n=== Track A leaderboard (optimal-move agreement) ===")
    print(f"{'model':<20}{'optimal%':>9}{'regret':>8}{'illegal%':>10}"
          f"{'err%':>6}{'lat(s)':>8}")
    for s in order:
        print(f"{s['model']:<20}{s['optimal_move_pct']:>9}"
              f"{s['mean_norm_regret']:>8}{s['illegal_pct']:>10}"
              f"{s['error_pct']:>6}{s['mean_latency_s']:>8}")


if __name__ == "__main__":
    run()

"""
Generate the fixed benchmark set of DECISION positions.

A "decision position" is a game state where the player to move has >= 2 distinct
legal moves given the die they rolled — i.e. a real choice, not a forced move.
We play many seeded games with a semi-skilled policy (epsilon-greedy on the
oracle) to reach realistic mid-game states, and snapshot the interesting ones.

Positions are saved to positions.jsonl so every model is scored on the EXACT
same set (reproducible, and luck-free for Track A).
"""
from __future__ import annotations

import json
import random

from ludo import PLAYERS, new_state, distinct_legal_moves, apply_move, is_winner
from oracle import rank_moves


def _policy_pick(state, player, die, rng, eps=0.25):
    """Semi-skilled mover used only to advance generator games to realistic states."""
    moves, values, best = rank_moves(state, player, die)
    if not moves:
        return None
    if rng.random() < eps:
        return rng.choice(moves)
    top = [m for m, v in zip(moves, values) if v == best]
    return rng.choice(top)


def generate(n_positions=150, seed=42, players=PLAYERS,
             snapshot_prob=0.35, max_turns=4000, min_options=2):
    rng = random.Random(seed)
    out = []
    seen_hashes = set()
    game = 0
    while len(out) < n_positions:
        game += 1
        state = new_state(players)
        turn_order = list(players)
        ti = rng.randrange(len(turn_order))
        turns = 0
        while turns < max_turns and len(out) < n_positions:
            turns += 1
            player = turn_order[ti]
            die = rng.randint(1, 6)
            moves = distinct_legal_moves(state, player, die)

            if len(moves) >= min_options and rng.random() < snapshot_prob:
                key = _hash(state, player, die)
                if key not in seen_hashes:
                    seen_hashes.add(key)
                    out.append({
                        "id": len(out),
                        "game": game,
                        "state": {p: list(v) for p, v in state.items()},
                        "player": player,
                        "die": die,
                        "n_options": len(moves),
                    })

            if moves:
                m = _policy_pick(state, player, die, rng)
                state = apply_move(state, player, m)
                if is_winner(state, player):
                    break
                if die == 6:
                    continue          # roll again (extra turn)
            ti = (ti + 1) % len(turn_order)
    return out


def _hash(state, player, die):
    return json.dumps([player, die, {p: state[p] for p in sorted(state)}],
                      sort_keys=True)


def save(positions, path="positions.jsonl"):
    with open(path, "w") as f:
        for p in positions:
            f.write(json.dumps(p) + "\n")


def load(path="positions.jsonl"):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    pos = generate(n_positions=n)
    save(pos)
    print(f"Generated {len(pos)} decision positions -> positions.jsonl")
    print("avg options/position:",
          round(sum(p["n_options"] for p in pos) / len(pos), 2))

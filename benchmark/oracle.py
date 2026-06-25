"""
Reference policy ("oracle") for scoring decisions.

This is a strong 1-ply heuristic, NOT proven game-theoretic optimal — Ludo's
full tree is intractable. We score a model by how often it matches this
reference's best move, plus how much value it leaves on the table ("regret").
The heuristic is intentionally simple and documented so the benchmark is
transparent and reproducible.

Value of a position, from `player`'s perspective:
    own_progress  - 0.5 * opponents_progress  - capture_threat

  * own_progress         rewards advancing, reaching home column, finishing,
                         and sitting on safe squares.
  * opponents_progress   subtracting it means CAPTURING an opponent (which
                         sends them back to base, dropping their progress) is
                         rewarded in proportion to how advanced they were.
  * capture_threat       penalizes leaving your own tokens where an opponent
                         could land on them next turn (exact-die capture,
                         probability ~1/6 each).
"""
from __future__ import annotations

from ludo import (FINISH, SAFE, TRACK_LEN, abs_square, token_progress,
                  distinct_legal_moves, apply_move)

CAPTURE_RISK_VALUE = 25.0   # how bad it is to be captured
ROLL_PROB = 1.0 / 6.0


def heuristic_value(state, player):
    own = 0.0
    for rel in state[player]:
        own += token_progress(rel)
        if 51 <= rel <= 55:
            own += 8                       # safe in the home column
        elif 0 <= rel <= 50 and abs_square(player, rel) in SAFE:
            own += 4                       # on a safe square

    opp = 0.0
    for p in state:
        if p == player:
            continue
        for rel in state[p]:
            opp += token_progress(rel)

    threat = 0.0
    for rel in state[player]:
        if not (0 <= rel <= 50):
            continue
        a = abs_square(player, rel)
        if a in SAFE:
            continue
        for p in state:
            if p == player:
                continue
            hit = False
            for orel in state[p]:
                if 0 <= orel <= 50:
                    d = (a - abs_square(p, orel)) % TRACK_LEN
                    if 1 <= d <= 6:
                        hit = True
                        break
            if hit:
                threat += CAPTURE_RISK_VALUE * ROLL_PROB

    return own - 0.5 * opp - threat


def rank_moves(state, player, die):
    """
    Return (moves, values, best_value) where `values[i]` is the heuristic value
    of the resulting state for moves[i], and best_value is the max.
    """
    moves = distinct_legal_moves(state, player, die)
    values = [heuristic_value(apply_move(state, player, m), player) for m in moves]
    best = max(values) if values else 0.0
    return moves, values, best


def best_move_ids(moves, values, best, eps=1e-9):
    """All move ids whose value ties the best (so ties count as correct)."""
    return {m["id"] for m, v in zip(moves, values) if abs(v - best) <= eps}

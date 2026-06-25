"""
No-API sanity checks: engine completes games, positions have real choices,
oracle returns a best move, parser is robust. Run: python selftest.py
"""
from __future__ import annotations

import random

from ludo import (PLAYERS, new_state, distinct_legal_moves, apply_move,
                  is_winner, FINISH)
from oracle import rank_moves, best_move_ids
from parse import extract_move_id
import positions as pos_mod


def test_games_finish(n=300):
    rng = random.Random(1)
    finished = 0
    for g in range(n):
        state = new_state()
        order = list(PLAYERS)
        ti = 0
        for _ in range(8000):
            p = order[ti]
            d = rng.randint(1, 6)
            moves = distinct_legal_moves(state, p, d)
            if moves:
                state = apply_move(state, p, rng.choice(moves))
                if is_winner(state, p):
                    finished += 1
                    break
                if d == 6:
                    continue
            ti = (ti + 1) % len(order)
    assert finished == n, f"only {finished}/{n} games finished"
    print(f"[ok] {n}/{n} random 4-player games reached a winner")


def test_positions_have_choices():
    pos = pos_mod.generate(n_positions=40, seed=7)
    assert len(pos) == 40
    assert all(p["n_options"] >= 2 for p in pos)
    avg = sum(p["n_options"] for p in pos) / len(pos)
    print(f"[ok] 40 decision positions, all with >=2 options (avg {avg:.2f})")


def test_oracle_and_parser():
    pos = pos_mod.generate(n_positions=10, seed=9)
    for p in pos:
        moves, values, best = rank_moves(p["state"], p["player"], p["die"])
        assert moves and len(values) == len(moves)
        bids = best_move_ids(moves, values, best)
        assert bids and bids.issubset({m["id"] for m in moves})
    valid = [1, 2, 3]
    assert extract_move_id('{"move": 2}', valid) == 2
    assert extract_move_id('I choose move 3 because...', valid) == 3
    assert extract_move_id('```json\n{"move":1}\n```', valid) == 1
    assert extract_move_id('the answer is 99', valid) is None
    assert extract_move_id('', valid) is None
    print("[ok] oracle returns best move(s); parser handles JSON/prose/garbage")


if __name__ == "__main__":
    test_games_finish()
    test_positions_have_choices()
    test_oracle_and_parser()
    print("\nAll self-tests passed.")

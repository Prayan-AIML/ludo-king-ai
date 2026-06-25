"""
Ludo rules engine (headless) — shared by the benchmark.

Positions are represented per player as a list of 4 token "relative" positions:
  -1            = in base (home yard); must roll a 6 to leave
   0..50        = on the 52-square shared track, measured from THIS player's start
   51..55       = in this player's private 6-square home column
   56 (FINISH)  = finished (reached home/center)

The shared track is a single 52-square loop. A token's absolute square is
  (START[player] + rel) % 52   for rel in 0..50.
Players start 13 squares apart, so captures happen when two tokens share an
absolute square (and that square is not a "safe" square).
"""
from __future__ import annotations

PLAYERS = ["red", "green", "yellow", "blue"]
START = {"red": 0, "green": 13, "yellow": 26, "blue": 39}
SAFE = {0, 13, 26, 39, 8, 21, 34, 47}   # 4 start squares + 4 star squares
FINISH = 56
TRACK_LEN = 52


def new_state(players=PLAYERS):
    return {p: [-1, -1, -1, -1] for p in players}


def abs_square(player, rel):
    """Absolute 0..51 track square for a token on the main track, else None."""
    if 0 <= rel <= 50:
        return (START[player] + rel) % TRACK_LEN
    return None


def token_progress(rel):
    """A scalar 'how far along' value used by the oracle heuristic."""
    if rel == -1:
        return 0
    if rel == FINISH:
        return 56 + 20          # finished is worth a big bonus
    return rel


def _captures_for_landing(state, player, to_rel):
    """List of (opponent, token_index) captured by landing on `to_rel`."""
    caps = []
    if not (0 <= to_rel <= 50):
        return caps             # home column / finish can't capture
    a = abs_square(player, to_rel)
    if a in SAFE:
        return caps             # safe squares never capture
    for opp in state:
        if opp == player:
            continue
        for j, orel in enumerate(state[opp]):
            if 0 <= orel <= 50 and abs_square(opp, orel) == a:
                caps.append((opp, j))
    return caps


def distinct_legal_moves(state, player, die):
    """
    All legal moves for `player` given `die`, de-duplicated to distinct
    OUTCOMES (two tokens stacked on the same square, or two tokens in base,
    are interchangeable and collapse to one option).

    Returns a list of move dicts in a neutral, stable order:
      {id, token, from_rel, to_rel, captures, desc}
    `id` is 1-based and is what a model is asked to choose.
    """
    seen = {}
    for i, rel in enumerate(state[player]):
        if rel == FINISH:
            continue
        if rel == -1:
            if die != 6:
                continue
            to_rel = 0
        else:
            to_rel = rel + die
            if to_rel > FINISH:
                continue
        caps = _captures_for_landing(state, player, to_rel)
        key = (rel, to_rel, frozenset(caps))
        if key not in seen:
            seen[key] = {"token": i, "from_rel": rel, "to_rel": to_rel,
                         "captures": caps}

    moves = sorted(seen.values(), key=lambda m: (m["from_rel"], m["to_rel"]))
    for idx, m in enumerate(moves, start=1):
        m["id"] = idx
        m["desc"] = describe_move(player, m)
    return moves


def apply_move(state, player, move):
    """Return a new state with `move` applied (captured opponents sent home)."""
    s = {p: list(v) for p, v in state.items()}
    s[player][move["token"]] = move["to_rel"]
    for (opp, j) in move["captures"]:
        s[opp][j] = -1
    return s


def is_winner(state, player):
    return all(rel == FINISH for rel in state[player])


def describe_move(player, m):
    fr, to = m["from_rel"], m["to_rel"]
    if fr == -1:
        s = f"Bring a {player} token out of base onto start square {abs_square(player, 0)}"
    elif to == FINISH:
        s = f"Move a {player} token from {loc(player, fr)} HOME (finish)"
    else:
        s = f"Move a {player} token from {loc(player, fr)} to {loc(player, to)}"
    if m["captures"]:
        who = ", ".join(f"{o}" for o, _ in m["captures"])
        s += f"  ← CAPTURES {who}!"
    return s


def loc(player, rel):
    """Human-readable location of a token at relative position `rel`."""
    if rel == -1:
        return "base"
    if rel == FINISH:
        return "finished"
    if 51 <= rel <= 55:
        return f"home-column step {rel - 50}/6"
    return f"square {abs_square(player, rel)} (track)"

"""
Render a decision position into a prompt for an LLM, and define the strict
output contract. The model must reply with JSON: {"move": <id>}.
"""
from __future__ import annotations

from ludo import abs_square, SAFE, FINISH

SYSTEM = (
    "You are an expert Ludo player. You will be given a board state, the die "
    "you just rolled, and a numbered list of your legal moves. Choose the move "
    "that maximizes your chances of winning.\n\n"
    "Rules reminder:\n"
    "- The shared track is squares 0-51, clockwise.\n"
    "- Landing exactly on a square occupied by an opponent sends that opponent "
    "back to base — UNLESS it is a safe square (marked SAFE).\n"
    f"- Safe squares are: {sorted(SAFE)}.\n"
    "- Each token must travel its full lap, then up a private 6-step home "
    "column, to finish. You need an exact roll to finish.\n"
    "- Capturing an opponent and advancing your most-progressed tokens are "
    "usually strong; avoid leaving a token where an opponent can land on it "
    "next turn.\n\n"
    'Respond with ONLY a JSON object of the form {"move": N} where N is the id '
    "of your chosen move. No other text."
)


def _token_line(player, rels):
    parts = []
    for rel in rels:
        if rel == -1:
            parts.append("base")
        elif rel == FINISH:
            parts.append("FINISHED")
        elif 51 <= rel <= 55:
            parts.append(f"home-col {rel-50}/6")
        else:
            a = abs_square(player, rel)
            tag = " SAFE" if a in SAFE else ""
            parts.append(f"sq{a}{tag}")
    return ", ".join(parts)


def build_user(position):
    state = position["state"]
    me = position["player"]
    die = position["die"]
    from ludo import distinct_legal_moves
    moves = distinct_legal_moves(state, me, die)

    lines = [f"You are playing {me.upper()}. You rolled a {die}.", "", "Board:"]
    # current player first, then others
    order = [me] + [p for p in state if p != me]
    for p in order:
        marker = "  (YOU)" if p == me else ""
        lines.append(f"  {p:<7}: {_token_line(p, state[p])}{marker}")

    lines += ["", "Your legal moves:"]
    for m in moves:
        lines.append(f"  {m['id']}. {m['desc']}")
    lines += ["", 'Reply with ONLY {"move": N}.']
    return "\n".join(lines), moves

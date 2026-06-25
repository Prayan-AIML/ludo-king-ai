"""
Parse an LLM's reply into a chosen move id. Robust to extra prose / markdown.
Returns an int id, or None if nothing usable / out of range.
"""
from __future__ import annotations

import json
import re


def extract_move_id(text, valid_ids):
    if not text:
        return None
    valid = set(valid_ids)

    # 1) Try strict / embedded JSON object with a "move" key.
    for match in re.finditer(r"\{[^{}]*\}", text, re.DOTALL):
        try:
            obj = json.loads(match.group(0))
        except Exception:
            continue
        if isinstance(obj, dict) and "move" in obj:
            try:
                n = int(obj["move"])
            except (TypeError, ValueError):
                continue
            if n in valid:
                return n

    # 2) Look for "move": N anywhere.
    m = re.search(r'"?move"?\s*[:=]\s*(\d+)', text, re.IGNORECASE)
    if m and int(m.group(1)) in valid:
        return int(m.group(1))

    # 3) Last resort: a bare integer that is a valid id.
    nums = [int(x) for x in re.findall(r"\d+", text)]
    for n in nums:
        if n in valid:
            return n
    return None

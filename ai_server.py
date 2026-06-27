#!/usr/bin/env python3
"""
Tiny local backend for the Ludo King "Yellow AI" trash-talk panel.

Why this exists
---------------
The browser game (play.html) used to ask you to paste your OpenAI key into a box
and then called OpenAI *directly from the browser*. That leaks your key to anyone
looking at the page and means the live GitHub Pages site can't taunt at all.

This little server keeps the key SERVER-SIDE (loaded from a local .env file) and
exposes two endpoints the game calls:

    POST /api/taunt   ->  one short, kid-friendly taunt/quip for a game event
    POST /api/chat    ->  a short in-character reply to whatever you typed

Run it:
    pip install flask openai python-dotenv
    python3 ai_server.py
Then open  http://localhost:5000/play.html  in your browser.

The server also serves the static game files, so you only need this one process.
"""

import os
import sys

from flask import Flask, request, jsonify, send_from_directory

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional; you can also just export the env vars yourself.
    pass

try:
    from openai import OpenAI
except ImportError:
    sys.exit("The 'openai' package isn't installed.\nRun:  pip install openai")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-nano")
API_KEY = os.environ.get("OPENAI_API_KEY")

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)

# One shared client (created lazily so the server still boots without a key, e.g.
# so the static game keeps working and only the AI panel is disabled).
_client = None


def get_client():
    global _client
    if not API_KEY:
        return None
    if _client is None:
        _client = OpenAI(api_key=API_KEY, timeout=30)
    return _client


# The personality the Yellow AI plays. Kept short, friendly, and KID-SAFE.
PERSONA = (
    "You are 'Yellow', a cheeky but good-natured AI opponent in a game of Ludo "
    "against a kid. You banter and gently trash-talk, but you are always "
    "kid-friendly: no insults about looks/intelligence/family, no profanity, "
    "nothing mean-spirited or scary. Think playful schoolyard rival, not bully. "
    "Keep every reply to ONE short sentence (14 words or fewer). No emojis unless "
    "they're tame. Never break character or mention being an AI model."
)


def ai_reply(user_content: str, max_tokens: int = 120) -> str:
    """Call gpt-5.4-nano via the Responses API and return one short line."""
    client = get_client()
    if client is None:
        # No key configured: hand back a safe canned line so the UI still works.
        return "(Add an OPENAI_API_KEY to .env so I can actually talk back!)"
    r = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": PERSONA},
            {"role": "user", "content": user_content},
        ],
        reasoning={"effort": "low"},   # without this, output_text can come back empty
        text={"verbosity": "low"},
        max_output_tokens=max_tokens,
    )
    text = (r.output_text or "").strip()
    # Keep it to a single line no matter what.
    return text.split("\n")[0].strip() or "Ha! You got lucky that time."


def describe_situation(data: dict) -> str:
    """Turn the game state JSON from the browser into a short English prompt."""
    whose_turn = data.get("turn", "unknown")
    winning = data.get("winning")          # "red" (human), "yellow" (AI), or "tied"
    last_move = data.get("lastMove", "")   # e.g. "the AI captured a token"
    event = data.get("event", "")          # e.g. "win", "capture", "roll"

    parts = []
    if event:
        parts.append(f"Game event: {event}.")
    if last_move:
        parts.append(f"What just happened: {last_move}.")
    if whose_turn:
        who = "the human's" if whose_turn == "red" else "your (Yellow's)"
        parts.append(f"It is now {who} turn.")
    if winning == "yellow":
        parts.append("You (Yellow) are currently ahead.")
    elif winning == "red":
        parts.append("The human is currently ahead.")
    elif winning == "tied":
        parts.append("The game is roughly even.")

    situation = " ".join(parts) if parts else "A normal moment in the Ludo game."
    return (
        situation
        + " Give ONE short, fun, kid-friendly taunt or quip reacting to this, "
        + "in character as Yellow."
    )


@app.route("/api/taunt", methods=["POST"])
def api_taunt():
    data = request.get_json(silent=True) or {}
    try:
        line = ai_reply(describe_situation(data), max_tokens=120)
        return jsonify({"taunt": line, "model": MODEL})
    except Exception as e:  # noqa: BLE001  (surface the error to the UI nicely)
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400
    # Light context so the reply fits the game.
    ctx = describe_situation({k: data.get(k) for k in ("turn", "winning", "lastMove")})
    prompt = (
        f"The human says to you: \"{message}\".\n"
        f"Current game context: {ctx}\n"
        "Reply in character with ONE short, friendly, playful line."
    )
    try:
        line = ai_reply(prompt, max_tokens=160)
        return jsonify({"reply": line, "model": MODEL})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "model": MODEL, "key_loaded": bool(API_KEY)})


# --- Serve the static game so one process is all you need -------------------
@app.route("/")
def root():
    return send_from_directory(HERE, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(HERE, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    if not API_KEY:
        print("WARNING: OPENAI_API_KEY not set — AI taunts will be disabled.")
        print("Create a .env file with OPENAI_API_KEY=... and OPENAI_MODEL=gpt-5.4-nano")
    print(f"Ludo King AI server on http://localhost:{port}  (model: {MODEL})")
    app.run(host="127.0.0.1", port=port, debug=False)

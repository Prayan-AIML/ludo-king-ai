# 🎲 Ludo King — Play vs AI

A browser-based **Ludo game where you play against an AI opponent**, with an optional
AI chat/trash-talk panel powered by the OpenAI API.

## ▶️ Play it now (live link)

**https://prayan-aiml.github.io/ludo-king-ai/**

No install, no key needed to play — just open the link and roll the dice.

## How to play

- You are **🔴 Red** (top-left). The AI is **🟡 Yellow** (bottom-right).
- Click **Roll Dice**.
- **Roll a 6** to bring a token out of its base.
- Tokens that can move **glow** — click one to move it.
- Land on an AI token (on a non-star square) to **capture** it and send it back to base. 💥
- **Rolling a 6 = an extra turn.** Get all 4 of your tokens to the center to **win**.
- **New Game** resets the board.

## AI feature

The Yellow AI opponent can now **trash-talk for real**, powered by **OpenAI
`gpt-5.4-nano`** — and the API key is kept **server-side**, never in the browser.

A tiny local backend, **`ai_server.py`** (Flask), holds the key and exposes:

| Endpoint | What it does |
|----------|--------------|
| `POST /api/taunt` | Takes the game situation (whose turn, who's winning, the last move/event) and returns **one short, fun, kid-friendly taunt** in character as Yellow. The game calls this automatically when the AI captures a token or when someone wins. |
| `POST /api/chat`  | Takes whatever you type in the chat box (plus light game context) and returns a short in-character reply. |

`play.html` now calls these endpoints instead of asking you to paste a key into
the page (the old in-browser key box has been removed — keys never touch the
browser). If the server isn't running, the game still plays perfectly; the
taunts just stay quiet.

### Run the AI feature locally

```bash
# 1. install the backend deps
pip install -r requirements-ai.txt          # flask, openai, python-dotenv

# 2. create a .env next to ai_server.py (this file is gitignored)
#    OPENAI_API_KEY=sk-...your key...
#    OPENAI_MODEL=gpt-5.4-nano

# 3. start the server (it also serves the game files)
python3 ai_server.py

# 4. open the game in your browser
#    http://localhost:5000/play.html
```

Roll the dice, let the Yellow AI capture one of your tokens, and watch it taunt
you — or type into the chat box to banter back. The taunts are constrained to be
**kid-friendly** (a system persona forbids insults, profanity, and anything
mean-spirited).

> Security: the OpenAI key lives only in your local `.env` (which is in
> `.gitignore`) and is read by `ai_server.py` on the server. It is never sent to
> or stored in the browser.

## Optional: terminal chat (bonus)

The game is 100% playable offline. The bonus `chat.py` script (below) is a
separate terminal-only chat if you just want to talk to the model directly.

## Files

| File | What it is |
|------|------------|
| `index.html` | Landing page (links to Play / Benchmark / Watch). |
| `play.html` | The full Ludo game + AI chat/taunt panel. |
| `ai_server.py` | Local Flask backend that holds the OpenAI key and powers `/api/taunt` and `/api/chat`. |
| `requirements-ai.txt` | Python deps for `ai_server.py`. |
| `chat.py` | A bonus terminal-only chat script (OpenAI, remembers messages within one run). |

### Running `chat.py` (optional)

```bash
pip install openai
python3 chat.py
```

Then paste your OpenAI key when prompted. It remembers the conversation for that
session only and forgets everything when you quit.

## Tech

Pure HTML/CSS/JavaScript — no build step, no framework. The Ludo engine (52-cell
track, home columns, captures, win detection, and the AI's move heuristic) runs
entirely in the browser.

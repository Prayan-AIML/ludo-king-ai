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

## Optional: chat / taunts with the AI

The game is 100% playable offline. If you paste an **OpenAI API key**
(starts with `sk-`, from <https://platform.openai.com/account/api-keys>) into the
box in the chat panel, the Yellow AI will banter with you and taunt you when it
captures a piece or wins.

> Your key is used only in your own browser to call the OpenAI API directly and is
> never stored or sent anywhere else. Don't paste your key on a shared/public computer.

## Files

| File | What it is |
|------|------------|
| `index.html` | The full Ludo game + chat (this is the app the live link serves). |
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

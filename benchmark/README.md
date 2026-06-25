# 🎲 Ludo LLM Benchmark — Track A (Decision Quality)

Benchmarks how well LLMs (OpenAI, Anthropic, Google) make **Ludo move
decisions**, with the luck of the dice removed. Each model is scored on the
**same fixed set of decision positions**: it sees the board + die + its legal
moves, picks one, and we compare its choice to a strong reference policy.

## Why this design

Ludo is mostly luck — head-to-head win rates mostly measure dice. Track A
removes luck by scoring *individual decisions* against a reference ("oracle"),
so the score reflects **judgement**, not rolls. (Head-to-head play with shared
dice seeds is "Track B" — not built yet.)

## Metrics (per model)

| Metric | Meaning |
|---|---|
| `optimal_move_pct` | % of positions where the model picked a reference-best move (ties count) |
| `mean_norm_regret` | how much value it left on the table, 0 (best) … 1 (worst), averaged |
| `illegal_pct` | % of replies that didn't yield a legal move id (format/rule failures) |
| `error_pct` | % of API/network errors |
| `mean_latency_s` | average response time |
| `tokens_in/out` | token usage (for cost) |

## Run it

**Today, with no API keys** (baselines prove the whole pipeline works):
```bash
python3 selftest.py     # engine + oracle + parser sanity checks
python3 run.py          # runs Random (floor) + Oracle (ceiling) baselines
```

**With models** — install SDKs and set whichever keys you have:
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...           # or GEMINI_API_KEY
python3 run.py
```
Models without a key are skipped automatically — add them as keys arrive.

## Files

| File | Role |
|---|---|
| `ludo.py` | Rules engine (track, legal moves, captures, win) — validated to 52-square loop |
| `oracle.py` | Reference policy: 1-ply heuristic that defines the "best" move |
| `positions.py` | Generates the fixed `positions.jsonl` decision set (seeded) |
| `prompt.py` | Renders a position to a prompt + the strict `{"move": N}` contract |
| `parse.py` | Extracts the chosen move id from a model reply (robust to prose/markdown) |
| `providers.py` | OpenAI / Anthropic / Google adapters behind one `decide()` method |
| `config.py` | **Edit model names here.** Which models to run, position count |
| `run.py` | Runs the benchmark, writes `results.csv` + `summary.json`, prints leaderboard |
| `selftest.py` | No-API correctness checks |

## Notes / honesty

- The oracle is a **strong heuristic, not proven-optimal** (Ludo's full tree is
  intractable). It's transparent and documented in `oracle.py`; scores are
  "agreement with a strong reference," which is the standard honest framing.
- Model IDs in `config.py` are the latest as of June 2026 — verify against each
  provider's `/models` endpoint before a paid run.
- Cost: each position = one API call per model. With 150 positions and 3 models
  that's 450 calls. Tune `N_POSITIONS` in `config.py` to control spend.

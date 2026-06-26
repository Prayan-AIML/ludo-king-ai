"""
Which models to benchmark. EDIT THE `model` STRINGS HERE if a provider renames
a model — nothing else needs to change.

`kind` is one of: openai | anthropic | google | random | oracle
  - random : picks a random legal move    (lower-bound baseline, no key needed)
  - oracle : always picks the reference best move (upper bound, no key needed)

Real providers are skipped automatically if their API key env var is missing,
so you can run the baselines today and add models as keys arrive.

Model names below are the latest as of June 2026 — verify against each
provider's /models endpoint before a paid run.
"""

MODELS = [
    # ---- baselines (always run, no API key needed) ----
    {"label": "Random (floor)",   "kind": "random", "model": None},
    {"label": "Oracle (ceiling)", "kind": "oracle", "model": None},

    # ---- models under test ----
    {"label": "GPT-5.4 nano",     "kind": "openai",    "model": "gpt-5.4-nano"},
    {"label": "Gemini 2.5 Flash", "kind": "google",    "model": "gemini-2.5-flash"},
    {"label": "Claude Opus 4.8",  "kind": "anthropic", "model": "claude-opus-4-8"},  # awaiting key — auto-skipped
]

# Display colors for the web leaderboard (by label).
COLORS = {
    "Oracle (ceiling)": "#34b27b",
    "Random (floor)":   "#9aa3b2",
    "GPT-5.4 nano":     "#3d8bd4",
    "Gemini 2.5 Flash": "#6c5ce7",
    "Claude Opus 4.8":  "#e07a3f",
}
NOTES = {
    "Oracle (ceiling)": "not an AI — a built-in expert that always plays the best move (the 100% ceiling)",
    "Random (floor)":   "not an AI — picks a legal move blindly, ignoring the board (the guessing floor)",
}

# Number of decision positions in the benchmark set (more = lower variance, more cost).
N_POSITIONS = 20
SEED = 42

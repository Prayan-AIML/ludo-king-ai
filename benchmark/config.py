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

    # ---- flagships ----
    {"label": "GPT-5.5",          "kind": "openai",    "model": "gpt-5.5"},
    {"label": "Claude Opus 4.8",  "kind": "anthropic", "model": "claude-opus-4-8"},
    {"label": "Gemini 3.1 Pro",   "kind": "google",    "model": "gemini-3.1-pro"},

    # ---- cheaper / faster tiers (uncomment to add a price/perf axis) ----
    # {"label": "GPT-5.5 mini",     "kind": "openai",    "model": "gpt-5.5-mini"},
    # {"label": "Claude Haiku 4.5", "kind": "anthropic", "model": "claude-haiku-4-5"},
    # {"label": "Gemini 3.5 Flash", "kind": "google",    "model": "gemini-3.5-flash"},
]

# Number of decision positions in the benchmark set (more = lower variance, more cost).
N_POSITIONS = 150
SEED = 42

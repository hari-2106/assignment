# Cordilla Systems, AI Engineer Exercise — Impact Framing, Agent Build, Monitoring

## Setup

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

Tested against Python 3.11+ with the exact pinned versions above. If you'd rather work in a notebook than plain scripts (either is fine, see the take-home packet), `pip install -r requirements-notebook.txt` instead (adds Jupyter on top of the same pinned core).

`requirements.txt` also pins `langgraph`, `streamlit`, `requests`, `groq`, `python-dotenv`, and
`inspect_ai` — added on top of the starter's original pins to build the agent (see
`RESEARCH-LOG.md` for why).

## Running the agent

Run everything from the repo root (relative paths in the code assume it).

    python -m agent.run

**Not** `python agent/run.py` — that breaks the `agent.*` package import (Python doesn't put
the repo root on `sys.path` when you run a script by relative path).

This loads `model/model.pkl`, scores `data/accounts_to_score.csv`, and writes
`agent/output/worklist.csv` and `monitoring/latest_report.json`. It also prints a summary
(tier counts, accounts needing review, drafts generated, monitoring status).

## Running the dashboard

    streamlit run agent/ui/app.py

Reads the two files above (run the agent at least once first, or use the in-app "Run agent
now" button). Three tabs: **Worklist** (filterable table, per-account detail with reason codes
and drafted outreach, a live "regenerate draft" button), **Monitoring** (all five checks with
pass/warn/fail status), and **Ask** (a domain-grounded Q&A chatbot — see below). The sidebar
also has a "What do these terms mean?" glossary for anyone unfamiliar with the sales/data terms.

## Optional: a real LLM call instead of the mock (outreach drafting)

No LLM API key is provided for this exercise (see the take-home packet), so outreach drafting
defaults to a documented mock (`agent/llm/client.py`). To use a real call instead, set an
environment variable before running:

    export GROQ_API_KEY=...          # Windows: $env:GROQ_API_KEY = "..."

Same interface either way — nothing else in the codebase changes.

## The "Ask" chatbot (a separate, real Groq feature — not part of the mock/Groq swap above)

`agent/chatbot.py` is a small Q&A assistant, always a real Groq call (`openai/gpt-oss-120b`,
streaming), grounded in a condensed domain-dictionary excerpt plus whichever account(s) a
question mentions (filtered from `agent/output/worklist.csv`, not the whole dataset). Requires
a `.env` file in the repo root with:

    GROQ_API_KEY=your-key-here

Try it from the CLI: `python -m agent.chatbot "Why is ACC-00533 a Hot account?"`, or use the
**Ask** tab in the Streamlit UI. Note: the full `DOMAIN-DICTIONARY.md` is too large for this
Groq org's 8000 TPM rate limit in one call, so the chatbot uses a hand-curated excerpt instead
(`CONDENSED_DICTIONARY` in `agent/chatbot.py`) — see `RESEARCH-LOG.md` for the full story.

Loading the model (already trained, don't retrain it):

    import pickle
    with open("model/model.pkl", "rb") as f:
        model = pickle.load(f)
    # model.predict_proba(df[feature_columns]), feature columns are listed below and in the take-home packet

Expected feature columns, in the order the model was trained on: `account_type`, `employee_count`, `industry`, `intent_score`, `mql_count_90d`, `trial_started`, `trial_active_users`, `web_touchpoints_90d`, `sales_contacts_90d`. `snapshot_date` and `account_id` are identifiers, not model inputs.

**Treat 2026-08-01 as "today" for this exercise.** Both CSVs are static snapshots generated as of that date. Any recency/age calculation (e.g. "how old is this account's snapshot") should use 2026-08-01 as the reference point, not your actual system clock.

## What's here

- `model/model.pkl`, a real, already-trained scikit-learn pipeline. Not retrained.
- `data/training_data.csv`, `data/accounts_to_score.csv` — provided, untouched.
- `scripts/explore_data.py` — one-off data/model exploration; findings are in `RESEARCH-LOG.md`.
- `scripts/make_charts.py` — generates the charts embedded in `PROPOSAL.html`.
- `agent/tools.py` — deterministic tools: `score_accounts`, `data_quality_gate`, `assign_tiers`,
  `assign_track`, `reason_codes` (plain-English, not raw column names). No LLM involved.
- `agent/llm/client.py` — the one non-deterministic *pipeline* tool (`OutreachDrafter`): a
  documented mock by default, a real Groq call if `GROQ_API_KEY` is set, same interface either way.
- `agent/chatbot.py` — a separate, always-real Groq-backed Q&A assistant (see above).
- `agent/graph.py`, `agent/run.py` — the LangGraph pipeline and its CLI entrypoint.
- `agent/ui/app.py` — the Streamlit dashboard (Worklist / Monitoring / Ask tabs + glossary).
- `agent/output/worklist.csv`, `agent/output/charts/` — a committed sample run's output/charts.
- `monitoring/checks.py` — input-quality, score-drift (PSI), tier-sanity, business-outcome-proxy
  (not yet runnable), and LLM-output-groundedness (via Inspect AI) checks.
- `monitoring/llm_eval.py` — the Inspect AI eval backing the groundedness check.
- `monitoring/latest_report.json` — output of the committed sample run.
- `DOMAIN-DICTIONARY.md` — reference for every column/term used here, including this repo's
  own implementation vocabulary (Tier, Track, `needs_review`, etc. — section 11).
- `PROPOSAL.md` — impact framing, agent design, monitoring design (required deliverable).
- `PROPOSAL.html` — the same substance, written for a non-technical/VP audience with charts
  and a concrete before/after example.
- `RESEARCH-LOG.md` — kept live throughout the build: hypotheses, data findings, AI
  prompts/responses, and multiple places an AI-drafted bug was caught and fixed.

## Working process

Commit as you actually go, small, real commits over time, not one commit at the end. We read the commit history as part of how you reason and work, not just the final diff.

**We'd genuinely like you to use AI here, assisted coding tools especially (Claude Code, Codex, Cursor, Antigravity, or similar), on your own accounts.** Dialpad doesn't provide one for this exercise. Disclose your actual sessions/prompts in `RESEARCH-LOG.md`, specific enough that we can see what shaped a decision, not a vague "used AI throughout."

## When you're done

Push this to a public git repo and send us the link. That's the submission. The presentation gets scheduled as a separate follow-up after that, not something to prepare beforehand.

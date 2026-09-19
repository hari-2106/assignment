# Cordilla Account Scoring

Turns a trained conversion-scoring model into an actual, prioritized worklist for sales reps —
plus the monitoring to know if it's still trustworthy, and a chatbot for anyone to ask
questions about it in plain English.

## Features

- **Scoring agent** — loads the pretrained model (`model/model.pkl`), scores every account in
  `data/accounts_to_score.csv`, and turns raw probabilities into a ranked, reasoned worklist:
  priority tier (Hot/Warm/Cold), which team should work it (SDR cold-outbound vs. Account
  Manager win-back), a plain-English explanation of why, and a drafted outreach message for
  top-priority accounts.
- **Data-quality safety gate** — flags accounts with stale or incomplete data and withholds
  auto-drafted outreach for them, rather than confidently acting on data it doesn't trust.
- **Monitoring** — five automated checks (input quality, score drift, tier balance, drafted-
  message accuracy, and a real-world outcome check) designed to catch the kind of *quiet*
  failure that doesn't crash anything but slowly stops being accurate.
- **Dashboard** — a Streamlit app to browse the worklist, inspect any account, see monitoring
  status at a glance, and re-run the agent, all without touching the command line.
- **Chatbot** — a Q&A assistant (Ask tab) for reps or analysts to ask things like "why is this
  account Hot?" or "what does needs_review mean?" in plain language.

## Prerequisites

- **Python 3.11** (the pinned dependency versions in `requirements.txt` are calibrated for
  3.11 specifically; other versions may not resolve cleanly).

## Setup

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

If you'd rather work in a notebook than plain scripts, `pip install -r requirements-notebook.txt`
instead (adds Jupyter on top of the same pinned core).

## Running the agent

Run everything from the repo root (relative paths in the code assume it):

    python -m agent.run

This loads `model/model.pkl`, scores `data/accounts_to_score.csv`, and writes
`agent/output/worklist.csv` and `monitoring/latest_report.json`, printing a summary (tier
counts, accounts needing review, drafts generated, monitoring status).

## Running the dashboard

    streamlit run agent/ui/app.py

Three tabs: **Worklist** (filterable table with per-account detail, reason codes, and drafted
outreach), **Monitoring** (all five checks with plain-English status), and **Ask** (the
chatbot — see below). A "What do these terms mean?" glossary lives in the sidebar.

## Enabling the chatbot (optional — a free Groq API key)

Everything above works with zero setup. The **Ask** tab is the one feature that needs a real
LLM key, since it's a genuine Q&A assistant rather than a scripted flow. If no key is
configured, the Ask tab shows a short "not set up" message instead of breaking, and every
other part of the app (scoring, worklist, monitoring) is completely unaffected.

To enable it:

1. Go to [console.groq.com](https://console.groq.com), sign up (free), and create an API key.
2. Create a file named `.env` in the repo root containing:

       GROQ_API_KEY=your-key-here

3. Restart the app. The Ask tab will pick it up automatically.

Try it from the CLI too: `python -m agent.chatbot "Why is ACC-00533 a Hot account?"` — it also
exits cleanly with a setup message if the key isn't configured, rather than crashing.

## Optional: a real LLM call for outreach drafting too

Separately from the chatbot, the agent's outreach-drafting step (`agent/llm/client.py`)
defaults to a documented, deterministic mock — no key needed. Setting the same `GROQ_API_KEY`
switches it to a real Groq call automatically; nothing else in the codebase changes.

## Repo contents

- `model/model.pkl` — the pretrained scikit-learn pipeline (not retrained).
- `data/training_data.csv`, `data/accounts_to_score.csv` — provided, untouched.
- `agent/tools.py` — deterministic scoring, data-quality gate, tiering, and reason codes.
- `agent/llm/client.py` — the outreach-drafting tool (mock by default, Groq if configured).
- `agent/chatbot.py` — the Ask-tab chatbot (always a real Groq call).
- `agent/graph.py`, `agent/run.py` — the LangGraph pipeline and its CLI entrypoint.
- `agent/ui/app.py` — the Streamlit dashboard.
- `agent/output/` — a committed sample run's worklist and charts.
- `monitoring/checks.py`, `monitoring/llm_eval.py` — the five monitoring checks.
- `monitoring/latest_report.json` — output of the committed sample run.
- `DOMAIN-DICTIONARY.md` — reference for every column and term used in this system.
- `PROPOSAL.md` — impact framing, agent design, and monitoring design.
- `PROPOSAL.html` — the same substance, illustrated for a non-technical audience.
- `RESEARCH-LOG.md` — the build's working log, kept live throughout.
- `scripts/explore_data.py`, `scripts/make_charts.py` — one-off data exploration and chart
  generation, not part of the running agent.

### Model input reference

    import pickle
    with open("model/model.pkl", "rb") as f:
        model = pickle.load(f)
    # model.predict_proba(df[feature_columns])

Feature columns, in the order the model expects: `account_type`, `employee_count`, `industry`,
`intent_score`, `mql_count_90d`, `trial_started`, `trial_active_users`, `web_touchpoints_90d`,
`sales_contacts_90d`. `snapshot_date` and `account_id` are identifiers, not model inputs.

`2026-08-01` is treated as "today" throughout this system — both CSVs are static snapshots
generated as of that date, so any recency/age calculation uses that as the reference point.

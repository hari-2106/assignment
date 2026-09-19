"""Domain-grounded Q&A assistant over the account worklist.

Separate from the scoring/agent pipeline — a small RAG-style helper for reps/analysts to ask
plain-English questions about a specific account or about terminology, grounded in:
  - DOMAIN-DICTIONARY.md (what every column/term actually means)
  - the relevant row(s) of agent/output/worklist.csv for whatever account(s) the question
    mentions, or a small aggregate summary if none are named

This is a REAL Groq call (not mocked) — requires GROQ_API_KEY in a local .env file. Uses the
model and call parameters as specified for this feature (openai/gpt-oss-120b, streaming).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterator

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_DICT_PATH = REPO_ROOT / "DOMAIN-DICTIONARY.md"
WORKLIST_PATH = REPO_ROOT / "agent" / "output" / "worklist.csv"
SCORE_PATH = REPO_ROOT / "data" / "accounts_to_score.csv"

MODEL = "openai/gpt-oss-120b"
ACCOUNT_ID_RE = re.compile(r"ACC-\d+", re.IGNORECASE)

# A condensed excerpt of DOMAIN-DICTIONARY.md, not the whole file: the full dictionary is
# ~10k tokens, which alone exceeds this Groq org's 8000 TPM rate limit before any question or
# answer is even added. A production version would retrieve only the relevant section per
# question (embeddings/keyword search over DOMAIN-DICTIONARY.md); for this prototype, a fixed
# condensed excerpt keeps every call small, fast, and within the free-tier limit.
CONDENSED_DICTIONARY = """
- account_type: Prospect (potential buyer, some qualification/interest), Suspect (possible
  buyer, not yet qualified), Former Customer (used to pay, no longer does — a win-back target).
- SDR: sales rep who does first-touch cold outreach into Prospects/Suspects.
- Account Manager (AM): owns the relationship with Former Customers — win-back here.
- Track: which persona should work the account. SDR_Outbound (Prospect/Suspect) or
  AM_WinBack (Former Customer).
- Tier (Hot/Warm/Cold): relative rank within THIS batch only (top 10% = Hot, next 30% = Warm,
  rest = Cold) — not an absolute probability cutoff. The model's raw scores are compressed
  (roughly 3.5%-27%), so this is a ranking convenience, not a claim about real conversion odds.
- needs_review: the agent doesn't trust this row enough to act on with full confidence
  (stale snapshot >365 days old, or a required field missing). Still shown, just flag for a
  human to sanity-check first. NOT set for missing intent_score alone — that's an expected
  ~40% vendor coverage gap the model already imputes around, not a red flag.
- intent_score: buying-interest signal from a third-party vendor, ~40% missing by design
  (partial vendor coverage). Missing does not mean "no interest," it means "no data."
- mql_count_90d, web_touchpoints_90d, sales_contacts_90d: counts of marketing-qualified
  leads / website interactions / sales outreach touches in the last 90 days.
- trial_started / trial_active_users: whether the account started a product trial, and how
  many users are active in it.
- reason_codes: deterministic (no LLM) explanation of the top signals behind an account's
  score — the model's biggest real inputs, phrased in plain English. Not a causal proof.
- draft_outreach: an LLM-drafted starting point for a rep's first message on Hot-tier
  accounts. Always meant to be reviewed/personalized before sending, never sent as-is.
- The ~4.1x "lift" number (top-decile accounts convert ~4x the overall base rate) is computed
  in-sample on historical training data, not validated on a held-out set — a directional
  number, not a guaranteed production conversion rate.
"""

SYSTEM_PROMPT_TEMPLATE = """You are a sales operations assistant for Cordilla Systems, helping \
reps and analysts understand account scores, priority tiers, and the sales/data terminology \
used in this system. Answer only from the reference material and account data given below — \
if the answer isn't in them, say so plainly instead of guessing or inventing facts. Keep \
answers concise and in plain business language, not technical jargon.

=== DOMAIN DICTIONARY (definitions of every column/term used here) ===
{domain_dictionary}

=== RELEVANT ACCOUNT DATA FOR THIS QUESTION ===
{account_context}
"""


def _load_env() -> None:
    """Load GROQ_API_KEY from the repo's .env if it isn't already set."""
    if os.environ.get("GROQ_API_KEY"):
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env")
        return
    except ImportError:
        pass
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def is_configured() -> bool:
    """True if a GROQ_API_KEY is available (env var or .env). Callers (CLI, Streamlit) should
    check this before calling ask() so a missing key fails as a clear message, not a crash.
    """
    _load_env()
    return bool(os.environ.get("GROQ_API_KEY"))


def _load_domain_dictionary() -> str:
    """Returns the condensed reference (see CONDENSED_DICTIONARY) rather than the full
    ~10k-token DOMAIN-DICTIONARY.md, which alone exceeds this Groq org's 8000 TPM rate limit.
    """
    return CONDENSED_DICTIONARY


def _filter_account_context(question: str, max_rows: int = 5) -> str:
    """Pull only the data relevant to the question — specific accounts if named, else a small
    aggregate summary — rather than dumping the full 300-row dataset into every request.
    """
    mentioned = {m.upper() for m in ACCOUNT_ID_RE.findall(question)}
    source = WORKLIST_PATH if WORKLIST_PATH.exists() else SCORE_PATH
    if not source.exists():
        return "(no account data available yet — run `python -m agent.run` first)"
    df = pd.read_csv(source)

    if mentioned:
        rows = df[df["account_id"].str.upper().isin(mentioned)]
        if rows.empty:
            return f"(no account found matching {sorted(mentioned)} in {source.name})"
        return rows.to_json(orient="records", indent=2)

    summary: dict = {"source_file": source.name, "row_count": len(df)}
    if "tier" in df.columns:
        summary["tier_counts"] = df["tier"].value_counts().to_dict()
    if "track" in df.columns:
        summary["track_counts"] = df["track"].value_counts().to_dict()
    if "needs_review" in df.columns:
        summary["needs_review_count"] = int(df["needs_review"].sum())
    if "probability" in df.columns:
        sample_cols = [c for c in ["account_id", "account_type", "tier", "probability"] if c in df.columns]
        top = df.sort_values("probability", ascending=False).head(max_rows)[sample_cols]
        summary["sample_top_accounts"] = top.to_dict(orient="records")
    return str(summary)


def ask(question: str) -> Iterator[str]:
    """Yields streamed response text chunks from Groq."""
    _load_env()
    from groq import Groq

    client = Groq()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        domain_dictionary=_load_domain_dictionary(),
        account_context=_filter_account_context(question),
    )
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=1,
        max_completion_tokens=2048,
        top_p=1,
        reasoning_effort="medium",
        stream=True,
        stop=None,
    )
    for chunk in completion:
        content = chunk.choices[0].delta.content
        if content:
            yield content


if __name__ == "__main__":
    import sys

    if not is_configured():
        print(
            "GROQ_API_KEY is not set. Create a .env file in the repo root with:\n"
            "  GROQ_API_KEY=your-key-here\n"
            "See README.md for how to get a free key from console.groq.com. The scoring "
            "agent itself (python -m agent.run) does not need this — only this chatbot does."
        )
        sys.exit(1)

    question = " ".join(sys.argv[1:]) or "How many accounts are in the Hot tier and why?"
    print(f"Q: {question}\n")
    for piece in ask(question):
        # Windows terminals default to cp1252, which can't encode every character an LLM
        # emits (e.g. non-breaking hyphens); the Streamlit UI renders UTF-8 fine regardless.
        safe = piece.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        print(safe, end="", flush=True)
    print()

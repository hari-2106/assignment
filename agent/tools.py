"""Deterministic tools the agent graph calls.

Everything in this module is plain, auditable Python — no LLM involved, no network calls.
The one non-deterministic tool (drafting outreach text) lives in agent/llm/client.py and is
deliberately kept separate so a bad/slow LLM call can never corrupt scoring, gating, or
routing decisions.

Thresholds and feature rankings below are grounded in scripts/explore_data.py's output —
see RESEARCH-LOG.md for the numbers behind each choice.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TODAY = pd.Timestamp("2026-08-01")

FEATURE_COLUMNS = [
    "account_type",
    "employee_count",
    "industry",
    "intent_score",
    "mql_count_90d",
    "trial_started",
    "trial_active_users",
    "web_touchpoints_90d",
    "sales_contacts_90d",
]

REQUIRED_COLUMNS = ["account_id", "account_type", "snapshot_date"] + FEATURE_COLUMNS

# model.named_steps['pre'].get_feature_names_out() mapped to
# model.named_steps['clf'].feature_importances_ (see scripts/explore_data.py). account_type
# and industry dummies contribute <0.02 each and are excluded from reason codes as noise.
FEATURE_IMPORTANCE = {
    "intent_score": 0.2712,
    "web_touchpoints_90d": 0.2139,
    "sales_contacts_90d": 0.2092,
    "employee_count": 0.1113,
    "trial_started": 0.0618,
    "trial_active_users": 0.0479,
    "mql_count_90d": 0.0443,
}

# Rows older than this (relative to TODAY) are flagged as stale rather than acted on blindly.
STALE_SNAPSHOT_DAYS = 365
# intent_score null rate observed in both training (40.2%) and scoring batch (38.7%).
INTENT_NULL_RATE_BASELINE = 0.40
INTENT_NULL_RATE_TOLERANCE = 0.10

# Fields the model pipeline does NOT impute for us (intent_score is median-imputed inside
# the pipeline itself, so it's allowed to be missing; these are not).
HARD_REQUIRED_NUMERIC = [
    "employee_count",
    "mql_count_90d",
    "trial_started",
    "trial_active_users",
    "web_touchpoints_90d",
    "sales_contacts_90d",
]


def load_model(path: str | Path = "model/model.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)


@dataclass
class DataQualityResult:
    dataset_ok: bool
    row_needs_review: pd.Series
    row_reasons: pd.Series
    dataset_metrics: dict


def check_schema(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def data_quality_gate(df: pd.DataFrame) -> DataQualityResult:
    """Per-row + dataset-level quality gate.

    `needs_review` means: the agent doesn't trust this row enough to act on it with full
    confidence, so a human should sanity-check it before anyone calls based on it alone. It
    is set when the snapshot is unparseable, over a year old (STALE_SNAPSHOT_DAYS), or missing
    a field the model needs beyond what its own imputation covers. It is NOT set just because
    `intent_score` is missing — that's a known ~40% vendor coverage gap the model already
    imputes around, not a reason to hold the account back. Flagged rows are still scored and
    shown, never hidden — this is "double-check before acting," not "ignore this account."

    At the dataset level, if quality has collapsed wholesale (see dataset_ok), the caller
    should abort the run rather than silently produce a confident-looking worklist from
    garbage input.
    """
    missing_cols = check_schema(df)
    if missing_cols:
        raise ValueError(f"accounts file missing required columns: {missing_cols}")

    snapshot = pd.to_datetime(df["snapshot_date"], errors="coerce")
    bad_date = snapshot.isna()
    age_days = (TODAY - snapshot).dt.days
    stale = age_days > STALE_SNAPSHOT_DAYS
    missing_hard = df[HARD_REQUIRED_NUMERIC].isna().any(axis=1)
    missing_intent = df["intent_score"].isna()

    reasons = []
    for idx in df.index:
        row_reasons = []
        if bad_date.loc[idx]:
            row_reasons.append("unparseable snapshot_date")
        elif stale.loc[idx]:
            row_reasons.append(f"stale snapshot ({int(age_days.loc[idx])}d old)")
        if missing_hard.loc[idx]:
            row_reasons.append("missing required numeric field(s)")
        if missing_intent.loc[idx]:
            row_reasons.append("intent_score missing (model-imputed)")
        reasons.append(row_reasons)

    row_reasons = pd.Series(reasons, index=df.index)
    # intent_score missing is NOT included here — the model imputes it and ~40% missingness
    # is an expected, known coverage gap, not a reason to withhold an account from a rep.
    row_needs_review = bad_date | missing_hard | stale

    intent_null_rate = float(missing_intent.mean())
    dataset_metrics = {
        "row_count": len(df),
        "intent_null_rate": intent_null_rate,
        "intent_null_rate_baseline": INTENT_NULL_RATE_BASELINE,
        "intent_null_rate_within_tolerance": abs(intent_null_rate - INTENT_NULL_RATE_BASELINE)
        <= INTENT_NULL_RATE_TOLERANCE,
        "hard_missing_rate": float(missing_hard.mean()),
        "stale_rate": float(stale.mean()),
        "bad_date_rate": float(bad_date.mean()),
    }
    # Catastrophic-collapse abort condition — deliberately generous (50%) so a normal amount
    # of real-world messiness doesn't trip it, but a broken upstream feed does.
    dataset_ok = dataset_metrics["hard_missing_rate"] < 0.5 and dataset_metrics["bad_date_rate"] < 0.5

    return DataQualityResult(
        dataset_ok=dataset_ok,
        row_needs_review=row_needs_review,
        row_reasons=row_reasons,
        dataset_metrics=dataset_metrics,
    )


def score_accounts(model, df: pd.DataFrame) -> pd.Series:
    proba = model.predict_proba(df[FEATURE_COLUMNS])[:, 1]
    return pd.Series(proba, index=df.index, name="probability")


def assign_tiers(probability: pd.Series, hot_pct: float = 0.10, warm_pct: float = 0.30) -> pd.Series:
    """Percentile-based tiers, grounded in the batch's own score distribution.

    The model's predicted probabilities are heavily compressed (median ~5%, max ~20-27% —
    see RESEARCH-LOG.md), so a fixed absolute cutoff like "Hot = P > 0.5" would select zero
    accounts. Tiering off percentiles of the actual batch is the only threshold that works
    with this model's output shape.
    """
    hot_cut = probability.quantile(1 - hot_pct)
    warm_cut = probability.quantile(1 - hot_pct - warm_pct)
    tiers = pd.Series("Cold", index=probability.index)
    tiers[probability >= warm_cut] = "Warm"
    tiers[probability >= hot_cut] = "Hot"
    return tiers


def assign_track(account_type: pd.Series) -> pd.Series:
    """Prospect/Suspect -> SDR cold-outbound track; Former Customer -> AM win-back track."""
    return account_type.map(lambda t: "AM_WinBack" if t == "Former Customer" else "SDR_Outbound")


def _phrase_intent_score(val: float, med: float, above: bool) -> str:
    level = "strong" if above else "below-average"
    return f"shows {level} buying intent (score {val:.0f} vs. a typical {med:.0f})"


def _phrase_web_touchpoints(val: float, med: float, above: bool) -> str:
    if val == 0:
        return "has not visited the website recently"
    word = "more" if above else "less"
    return (
        f"has been {word} active on the website than usual "
        f"({val:g} visits in the last 90 days vs. a typical {med:g})"
    )


def _phrase_sales_contacts(val: float, med: float, above: bool) -> str:
    if val == 0:
        return "has had no sales contact yet in the last 90 days"
    word = "more" if above else "less"
    return (
        f"has had {word} contact with sales than typical "
        f"({val:g} touches in 90 days vs. a typical {med:g})"
    )


def _phrase_employee_count(val: float, med: float, above: bool) -> str:
    word = "larger" if above else "smaller"
    return f"is a {word} company by headcount ({val:g} employees vs. a typical {med:g})"


def _phrase_trial_started(val: float, med: float, above: bool) -> str:
    return "has started a free trial" if val >= 1 else "has not started a trial yet"


def _phrase_trial_active_users(val: float, med: float, above: bool) -> str:
    if val == 0:
        return "has no active trial users"
    word = "more" if above else "fewer"
    return f"has {word} active trial users than typical ({val:g} vs. a typical {med:g})"


def _phrase_mql_count(val: float, med: float, above: bool) -> str:
    if val == 0:
        return "has generated no marketing-qualified leads in the last 90 days"
    word = "more" if above else "fewer"
    return (
        f"generated {word} marketing-qualified leads than typical "
        f"({val:g} in 90 days vs. a typical {med:g})"
    )


# Plain-language phrasing for each feature — keeps reason codes readable by a sales rep
# instead of exposing raw column names and statistics jargon.
FEATURE_PHRASES = {
    "intent_score": _phrase_intent_score,
    "web_touchpoints_90d": _phrase_web_touchpoints,
    "sales_contacts_90d": _phrase_sales_contacts,
    "employee_count": _phrase_employee_count,
    "trial_started": _phrase_trial_started,
    "trial_active_users": _phrase_trial_active_users,
    "mql_count_90d": _phrase_mql_count,
}


def reason_codes(df: pd.DataFrame, top_n: int = 3) -> pd.Series:
    """Deterministic explainability: for each account, rank its top numeric signals by
    (feature importance x distance from the population median) and render each as a plain
    English sentence a rep can read without needing to know column names or medians, e.g.
    "has been more active on the website than usual (9 visits in the last 90 days vs. a
    typical 2)" instead of "web_touchpoints_90d: 9 (above median 2)".

    No LLM involved — this must stay available and reliable even if the LLM draft step is
    down or disabled.
    """
    medians = df[list(FEATURE_IMPORTANCE)].median()
    results = []
    for _, row in df.iterrows():
        scored = []
        for feat, importance in FEATURE_IMPORTANCE.items():
            val = row[feat]
            med = medians[feat]
            if pd.isna(val) or med == 0:
                continue
            relative = (val - med) / (abs(med) + 1e-6)
            scored.append((abs(relative) * importance, feat, val, med, relative))
        scored.sort(key=lambda x: -x[0])
        sentences = []
        for _, feat, val, med, relative in scored[:top_n]:
            sentences.append(FEATURE_PHRASES[feat](val, med, relative > 0))
        results.append(sentences)
    return pd.Series(results, index=df.index)

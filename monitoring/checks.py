"""Concrete monitoring checks for the account-scoring agent.

Designed around one specific failure mode: the *quiet* kind, where nothing crashes but the
output silently drifts out of sync with reality — the Cordilla story from the brief (an
earlier scoring effort looked fine in testing, then quietly stopped matching what reps saw in
the field, and nobody was watching the right signal to catch it while it happened).

Each check returns a small dict: {"status": "pass"|"warn"|"fail"|"not_runnable", ...evidence}.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PSI_WARN_THRESHOLD = 0.10
PSI_FAIL_THRESHOLD = 0.20

# Matches assign_tiers' default hot_pct in agent/tools.py.
EXPECTED_HOT_SHARE = 0.10
TIER_SHARE_WARN_RATIO = 2.0  # warn if actual/expected hot share > 2x or < 0.5x

CALIBRATION_WARN_GAP = 0.08
CALIBRATION_FAIL_GAP = 0.15


def check_input_quality(dq_metrics: dict) -> dict:
    """Wraps the dataset-level metrics agent.tools.data_quality_gate already computed."""
    issues = []
    status = "pass"

    if not dq_metrics["intent_null_rate_within_tolerance"]:
        issues.append(
            f"intent_score null rate {dq_metrics['intent_null_rate']:.1%} is outside the "
            f"expected {dq_metrics['intent_null_rate_baseline']:.0%} +/- tolerance band — "
            f"possible vendor coverage change."
        )
        status = "warn"

    if dq_metrics["hard_missing_rate"] > 0.05:
        issues.append(
            f"{dq_metrics['hard_missing_rate']:.1%} of rows are missing required fields."
        )
        status = "warn" if status == "pass" else status

    if dq_metrics["stale_rate"] > 0.30:
        issues.append(
            f"{dq_metrics['stale_rate']:.1%} of rows have snapshots older than a year."
        )
        status = "warn" if status == "pass" else status

    return {"status": status, "issues": issues, "metrics": dq_metrics}


def _psi_bucket_edges(reference: pd.Series, n_buckets: int = 10) -> np.ndarray:
    quantiles = np.linspace(0, 1, n_buckets + 1)
    edges = reference.quantile(quantiles).to_numpy(dtype=float)
    edges[0] = -np.inf
    edges[-1] = np.inf
    return np.unique(edges)


def check_score_distribution_drift(reference_scores: pd.Series, new_scores: pd.Series) -> dict:
    """Population Stability Index between the training-set predicted-probability distribution
    and a new batch's. This is the check aimed directly at the Cordilla story: a model that
    still runs fine but whose outputs have quietly shifted relative to what it was
    trained/validated on. Standard thresholds: PSI < 0.10 stable, 0.10-0.20 moderate shift
    (warn), > 0.20 significant shift (fail/alert).
    """
    edges = _psi_bucket_edges(reference_scores)
    ref_counts, _ = np.histogram(reference_scores, bins=edges)
    new_counts, _ = np.histogram(new_scores, bins=edges)

    ref_pct = np.clip(ref_counts / ref_counts.sum(), 1e-4, None)
    new_pct = np.clip(new_counts / new_counts.sum(), 1e-4, None)

    psi = float(np.sum((new_pct - ref_pct) * np.log(new_pct / ref_pct)))

    if psi < PSI_WARN_THRESHOLD:
        status = "pass"
    elif psi < PSI_FAIL_THRESHOLD:
        status = "warn"
    else:
        status = "fail"

    return {
        "status": status,
        "psi": psi,
        "reference_n": int(len(reference_scores)),
        "new_n": int(len(new_scores)),
    }


def check_tier_distribution_sanity(tiers: pd.Series) -> dict:
    """Catches threshold miscalibration or upstream feature breakage even when the raw score
    distribution's PSI looks fine — e.g. if a feature pipeline bug pushed a normally-rare
    combination of signals into every row, tiers could shift even if the marginal score
    distribution barely moves.
    """
    hot_share = float((tiers == "Hot").mean())
    ratio = hot_share / EXPECTED_HOT_SHARE if EXPECTED_HOT_SHARE else 0.0
    if (1 / TIER_SHARE_WARN_RATIO) <= ratio <= TIER_SHARE_WARN_RATIO:
        status = "pass"
    else:
        status = "warn"
    return {"status": status, "hot_share": hot_share, "expected_hot_share": EXPECTED_HOT_SHARE}


def check_business_outcome_proxy(
    flagged_accounts: pd.DataFrame | None = None,
    outcomes: pd.DataFrame | None = None,
) -> dict:
    """Calibration check: of accounts the agent flagged Hot N days ago, what fraction actually
    converted, broken out by predicted-probability decile? This is the single check that would
    have actually caught Cordilla's earlier quiet drift — a model whose *relative* ranking
    still looked fine but whose *predicted* rates no longer matched what reps were seeing
    close in the field.

    Precisely specified here, but NOT runnable today: conversion is measured over a 90-day
    window and this batch was scored on 2026-08-01, so no ground-truth outcomes exist yet for
    it. Once this agent has been running >=90 days, call this with:
      - flagged_accounts: historical worklist rows (account_id, probability, tier, ...)
      - outcomes: a dataframe of {account_id, converted_within_90d} joined from Salesforce
    It buckets by predicted-probability decile, compares actual vs. predicted conversion rate
    per bucket, and fails if any bucket's gap exceeds CALIBRATION_FAIL_GAP.
    """
    if flagged_accounts is None or outcomes is None:
        return {
            "status": "not_runnable",
            "reason": (
                "No ground-truth outcomes exist yet for this batch (conversion is a 90-day "
                "window; this batch was scored on 2026-08-01). See this function's docstring "
                "for the exact inputs and logic once outcomes are available."
            ),
        }

    merged = flagged_accounts.merge(outcomes, on="account_id", how="inner")
    merged["decile"] = pd.qcut(merged["probability"], 10, duplicates="drop")
    calibration = merged.groupby("decile", observed=True).agg(
        predicted=("probability", "mean"),
        actual=("converted_within_90d", "mean"),
        n=("account_id", "count"),
    )
    calibration["gap"] = (calibration["actual"] - calibration["predicted"]).abs()
    worst_gap = float(calibration["gap"].max())

    if worst_gap > CALIBRATION_FAIL_GAP:
        status = "fail"
    elif worst_gap > CALIBRATION_WARN_GAP:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "worst_gap": worst_gap,
        "calibration": calibration.reset_index().astype(str).to_dict("records"),
    }


def check_llm_output_groundedness(worklist_path: str = "agent/output/worklist.csv") -> dict:
    """Runs the Inspect AI numeric-groundedness eval (monitoring/llm_eval.py) against the
    drafted outreach text. Unlike the other checks, this one targets the LLM step
    specifically: does every number a draft states about an account actually appear in that
    account's real data? The mock backend always scores ~1.0 by construction (it only
    recombines given facts) — this check earns its value once a real generative backend
    (Groq) is active and could paraphrase, round, or invent a number.
    """
    try:
        from monitoring.llm_eval import run_groundedness_eval

        return run_groundedness_eval(worklist_path)
    except Exception as exc:  # pragma: no cover - defensive: eval infra shouldn't break scoring
        return {"status": "not_runnable", "reason": f"groundedness eval failed to run: {exc}"}


def build_report(
    dq_metrics: dict,
    reference_scores: pd.Series,
    new_scores: pd.Series,
    tiers: pd.Series,
) -> dict:
    return {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "input_quality": check_input_quality(dq_metrics),
        "score_drift": check_score_distribution_drift(reference_scores, new_scores),
        "tier_sanity": check_tier_distribution_sanity(tiers),
        "business_outcome_proxy": check_business_outcome_proxy(),
        "llm_output_groundedness": check_llm_output_groundedness(),
    }

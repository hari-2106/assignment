"""Generates the charts embedded in PROPOSAL.html.

Not part of the agent pipeline — a one-off visualization script, run manually:
    python scripts/make_charts.py

Writes PNGs into agent/output/charts/. Uses matplotlib only (already a pinned dependency),
so PROPOSAL.html stays fully offline/self-contained — no JS chart library, no CDN.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from agent import tools

OUT_DIR = Path("agent/output/charts")
COLORS = {"Hot": "#d62828", "Warm": "#f77f00", "Cold": "#8d99ae"}


def load_worklist() -> pd.DataFrame:
    return pd.read_csv("agent/output/worklist.csv")


def chart_funnel(wl: pd.DataFrame) -> None:
    stages = [
        ("Accounts scored", len(wl)),
        ("Confidently scored\n(not flagged for review)", int((~wl["needs_review"]).sum())),
        ("Hot tier\n(top priority this week)", int((wl["tier"] == "Hot").sum())),
        ("Draft outreach ready", int((wl["draft_outreach"].fillna("").astype(str).str.len() > 0).sum())),
    ]
    labels = [s[0] for s in stages]
    values = [s[1] for s in stages]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(labels, values, color=["#457b9d", "#457b9d", "#d62828", "#2a9d8f"])
    ax.invert_yaxis()
    ax.set_xlabel("Number of accounts")
    ax.set_title("From raw batch to a rep's actual worklist")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 3, bar.get_y() + bar.get_height() / 2, str(val), va="center")
    ax.set_xlim(0, max(values) * 1.15)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "funnel.png", dpi=150)
    plt.close(fig)


def chart_lift(model) -> None:
    train = pd.read_csv("data/training_data.csv")
    proba = tools.score_accounts(model, train)
    train = train.assign(proba=proba)
    train["decile"] = pd.qcut(train["proba"], 10, labels=False, duplicates="drop")
    summary = train.groupby("decile")["converted_within_90d"].mean() * 100
    overall = train["converted_within_90d"].mean() * 100

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(
        [f"D{i}" for i in summary.index],
        summary.values,
        color=["#d62828" if i == summary.index.max() else "#8d99ae" for i in summary.index],
    )
    ax.axhline(overall, color="#264653", linestyle="--", linewidth=1.5, label=f"Overall avg: {overall:.1f}%")
    ax.set_ylabel("Actual conversion rate (%)")
    ax.set_xlabel("Predicted-probability decile (D0 = lowest, D9 = highest / Hot-tier-equivalent)")
    ax.set_title("Top-decile accounts convert ~4x the overall rate (in-sample)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "lift.png", dpi=150)
    plt.close(fig)


def chart_tier_by_track(wl: pd.DataFrame) -> None:
    pivot = wl.groupby(["track", "tier"]).size().unstack(fill_value=0)
    pivot = pivot[[c for c in ["Hot", "Warm", "Cold"] if c in pivot.columns]]

    fig, ax = plt.subplots(figsize=(7, 4))
    pivot.plot(kind="bar", stacked=True, ax=ax, color=[COLORS[c] for c in pivot.columns])
    ax.set_ylabel("Number of accounts")
    ax.set_xlabel("Track")
    ax.set_title("Today's batch: tier mix by track")
    ax.legend(title="Tier")
    plt.xticks(rotation=0)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "tier_by_track.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model = tools.load_model()
    worklist = load_worklist()
    chart_funnel(worklist)
    chart_lift(model)
    chart_tier_by_track(worklist)
    print(f"Charts written to {OUT_DIR}/")

"""One-off data exploration to ground PROPOSAL.md numbers and monitoring thresholds.

Not part of the agent pipeline itself — run manually, read the printed output, and record
findings in RESEARCH-LOG.md. Treat 2026-08-01 as "today" per the brief.
"""

import pickle

import numpy as np
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


def load():
    train = pd.read_csv("data/training_data.csv")
    score = pd.read_csv("data/accounts_to_score.csv")
    with open("model/model.pkl", "rb") as f:
        model = pickle.load(f)
    return train, score, model


def describe_model(model):
    print("=" * 70)
    print("MODEL PIPELINE")
    print("=" * 70)
    print(type(model))
    print(model)
    try:
        print("\nsteps:", model.steps)
    except AttributeError:
        pass
    final_estimator = model
    try:
        final_estimator = model.steps[-1][1]
    except AttributeError:
        pass
    print("\nfinal estimator:", type(final_estimator))
    if hasattr(final_estimator, "feature_importances_"):
        print("feature_importances_:", final_estimator.feature_importances_)
    if hasattr(final_estimator, "coef_"):
        print("coef_:", final_estimator.coef_)
    try:
        print("\nfeature_names_in_ (pipeline):", model.feature_names_in_)
    except AttributeError:
        pass


def describe_training(train: pd.DataFrame):
    print("=" * 70)
    print("TRAINING DATA")
    print("=" * 70)
    print("rows:", len(train))
    print("\naccount_type counts:\n", train["account_type"].value_counts())
    print("\noverall conversion rate:", train["converted_within_90d"].mean())
    print(
        "\nconversion rate by account_type:\n",
        train.groupby("account_type")["converted_within_90d"].mean(),
    )
    print("\nintent_score null rate:", train["intent_score"].isna().mean())
    print(
        "\nconversion rate, intent_score null vs present:\n",
        train.assign(has_intent=train["intent_score"].notna())
        .groupby("has_intent")["converted_within_90d"]
        .mean(),
    )
    print(
        "\nconversion rate by trial_started:\n",
        train.groupby("trial_started")["converted_within_90d"].mean(),
    )
    print(
        "\nconversion rate by sales_contacts_90d bucket:\n",
        train.assign(
            contacted=np.where(train["sales_contacts_90d"] > 0, "contacted", "cold")
        )
        .groupby("contacted")["converted_within_90d"]
        .mean(),
    )
    print("\nnumeric describe:\n", train.describe())
    print("\nsnapshot_date range:", train["snapshot_date"].min(), "-", train["snapshot_date"].max())


def describe_scoring_batch(score: pd.DataFrame):
    print("=" * 70)
    print("SCORING BATCH (accounts_to_score.csv)")
    print("=" * 70)
    print("rows:", len(score))
    print("\naccount_type counts:\n", score["account_type"].value_counts())
    print("\nintent_score null rate:", score["intent_score"].isna().mean())
    print("\nnumeric describe:\n", score.describe())
    print(
        "\nsnapshot_date range:",
        score["snapshot_date"].min(),
        "-",
        score["snapshot_date"].max(),
    )
    age_days = (TODAY - pd.to_datetime(score["snapshot_date"])).dt.days
    print("\nsnapshot age (days) describe:\n", age_days.describe())


def score_distribution(train, score, model):
    print("=" * 70)
    print("SCORE DISTRIBUTIONS (predict_proba)")
    print("=" * 70)
    train_proba = model.predict_proba(train[FEATURE_COLUMNS])[:, 1]
    score_proba = model.predict_proba(score[FEATURE_COLUMNS])[:, 1]
    print("\ntrain predicted-proba describe:\n", pd.Series(train_proba).describe())
    print("\nscoring-batch predicted-proba describe:\n", pd.Series(score_proba).describe())
    print(
        "\ntrain proba deciles:\n",
        pd.Series(train_proba).quantile([0.1 * i for i in range(11)]),
    )
    print(
        "\nscoring-batch proba deciles:\n",
        pd.Series(score_proba).quantile([0.1 * i for i in range(11)]),
    )


if __name__ == "__main__":
    train, score, model = load()
    describe_model(model)
    describe_training(train)
    describe_scoring_batch(score)
    score_distribution(train, score, model)

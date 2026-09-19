"""LangGraph pipeline: load -> quality-gate -> score -> segment -> explain -> draft -> write.

Two conditional edges make the control flow real rather than decorative:
  1. data_quality_gate -> abort_and_alert: if input quality has collapsed wholesale, the
     graph refuses to score and ends the run instead of silently producing a confident-
     looking worklist from broken input (the exact failure mode the brief warns about).
  2. generate_reason_codes -> draft_outreach (skipped if there are zero Hot-tier accounts):
     the one LLM-backed step only runs when there's actually something to draft for.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from agent import tools
from agent.llm.client import get_drafter
from monitoring import checks

ACCOUNTS_PATH = "data/accounts_to_score.csv"
TRAINING_PATH = "data/training_data.csv"
MODEL_PATH = "model/model.pkl"
OUTPUT_DIR = Path("agent/output")
WORKLIST_PATH = OUTPUT_DIR / "worklist.csv"
MONITORING_REPORT_PATH = Path("monitoring/latest_report.json")

HOT_DRAFT_CAP = 20
TIER_SORT_ORDER = {"Hot": 0, "Warm": 1, "Cold": 2}


class AgentState(TypedDict, total=False):
    df: pd.DataFrame
    training_df: pd.DataFrame
    model: object
    dq_metrics: dict
    dq_needs_review: pd.Series
    dq_reasons: pd.Series
    dataset_ok: bool
    abort_reason: Optional[str]
    probability: pd.Series
    tiers: pd.Series
    track: pd.Series
    reason_codes: pd.Series
    drafts: dict
    worklist: pd.DataFrame
    monitoring_report: dict


def load_inputs(state: AgentState) -> dict:
    model = tools.load_model(MODEL_PATH)
    df = pd.read_csv(ACCOUNTS_PATH)
    training_df = pd.read_csv(TRAINING_PATH)
    missing = tools.check_schema(df)
    if missing:
        raise ValueError(f"{ACCOUNTS_PATH} missing required columns: {missing}")
    return {"df": df, "training_df": training_df, "model": model}


def data_quality_gate(state: AgentState) -> dict:
    result = tools.data_quality_gate(state["df"])
    return {
        "dq_metrics": result.dataset_metrics,
        "dq_needs_review": result.row_needs_review,
        "dq_reasons": result.row_reasons,
        "dataset_ok": result.dataset_ok,
    }


def route_after_quality_gate(state: AgentState) -> str:
    return "score_accounts" if state["dataset_ok"] else "abort_and_alert"


def abort_and_alert(state: AgentState) -> dict:
    reason = (
        "Data quality gate failed catastrophically "
        f"({state['dq_metrics']}). Aborting the run instead of scoring on broken input."
    )
    print(f"ABORT: {reason}")
    return {"abort_reason": reason}


def score_accounts(state: AgentState) -> dict:
    proba = tools.score_accounts(state["model"], state["df"])
    return {"probability": proba}


def segment_and_route(state: AgentState) -> dict:
    tiers = tools.assign_tiers(state["probability"])
    track = tools.assign_track(state["df"]["account_type"])
    return {"tiers": tiers, "track": track}


def generate_reason_codes(state: AgentState) -> dict:
    return {"reason_codes": tools.reason_codes(state["df"])}


def route_after_reason_codes(state: AgentState) -> str:
    hot_count = int((state["tiers"] == "Hot").sum())
    return "draft_outreach" if hot_count > 0 else "write_outputs"


def draft_outreach(state: AgentState) -> dict:
    drafter = get_drafter()
    df = state["df"]
    tiers = state["tiers"]
    probability = state["probability"]
    rc = state["reason_codes"]
    hot_idx = (
        probability[tiers == "Hot"].sort_values(ascending=False).index[:HOT_DRAFT_CAP]
    )
    drafts = {}
    for idx in hot_idx:
        account = df.loc[idx].to_dict()
        drafts[df.loc[idx, "account_id"]] = drafter.draft(account, rc.loc[idx])
    return {"drafts": drafts}


def write_outputs(state: AgentState) -> dict:
    df = state["df"].copy()
    df["probability"] = state["probability"]
    df["tier"] = state["tiers"]
    df["track"] = state["track"]
    df["needs_review"] = state["dq_needs_review"]
    df["quality_flags"] = state["dq_reasons"].apply("; ".join)
    df["reason_codes"] = state["reason_codes"].apply("; ".join)
    drafts = state.get("drafts", {})
    df["draft_outreach"] = df["account_id"].map(drafts).fillna("")

    df["_tier_sort"] = df["tier"].map(TIER_SORT_ORDER)
    df = df.sort_values(["_tier_sort", "probability"], ascending=[True, False]).drop(
        columns="_tier_sort"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(WORKLIST_PATH, index=False)
    return {"worklist": df}


def run_monitoring_checks(state: AgentState) -> dict:
    training_proba = state["model"].predict_proba(
        state["training_df"][tools.FEATURE_COLUMNS]
    )[:, 1]
    report = checks.build_report(
        dq_metrics=state["dq_metrics"],
        reference_scores=pd.Series(training_proba),
        new_scores=state["probability"],
        tiers=state["tiers"],
    )
    MONITORING_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MONITORING_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return {"monitoring_report": report}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_inputs", load_inputs)
    graph.add_node("data_quality_gate", data_quality_gate)
    graph.add_node("abort_and_alert", abort_and_alert)
    graph.add_node("score_accounts", score_accounts)
    graph.add_node("segment_and_route", segment_and_route)
    graph.add_node("generate_reason_codes", generate_reason_codes)
    graph.add_node("draft_outreach", draft_outreach)
    graph.add_node("write_outputs", write_outputs)
    graph.add_node("run_monitoring_checks", run_monitoring_checks)

    graph.add_edge(START, "load_inputs")
    graph.add_edge("load_inputs", "data_quality_gate")
    graph.add_conditional_edges(
        "data_quality_gate",
        route_after_quality_gate,
        {"score_accounts": "score_accounts", "abort_and_alert": "abort_and_alert"},
    )
    graph.add_edge("abort_and_alert", END)
    graph.add_edge("score_accounts", "segment_and_route")
    graph.add_edge("segment_and_route", "generate_reason_codes")
    graph.add_conditional_edges(
        "generate_reason_codes",
        route_after_reason_codes,
        {"draft_outreach": "draft_outreach", "write_outputs": "write_outputs"},
    )
    graph.add_edge("draft_outreach", "write_outputs")
    graph.add_edge("write_outputs", "run_monitoring_checks")
    graph.add_edge("run_monitoring_checks", END)

    return graph.compile()

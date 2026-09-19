"""Inspect AI eval: catches hallucinated/ungrounded outreach drafts.

The deterministic tools (scoring, the data-quality gate, reason codes) can't silently
hallucinate — only the one LLM-backed step (draft_outreach) can. This uses Inspect AI (the
UK AI Security Institute's open-source LLM eval framework) to score already-generated drafts
for numeric groundedness: does every number a draft states about an account actually appear
in that account's real data or reason codes, or did the model invent one?

This check is honestly limited today: the mock drafter only recombines facts it was already
given, so it will always score ~1.0 by construction. It starts earning its keep the moment a
real generative backend (Groq) is active, since a real model can paraphrase, round, or
outright invent a number that isn't in the account's data — exactly the kind of quiet,
non-crashing failure this whole monitoring design is built around.

Run:
    python -m monitoring.llm_eval
"""

from __future__ import annotations

import re

import pandas as pd
from inspect_ai import Task, eval, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

# Feature columns whose real values are legitimate for a draft to cite.
GROUNDING_FEATURE_COLUMNS = [
    "employee_count",
    "intent_score",
    "mql_count_90d",
    "trial_active_users",
    "web_touchpoints_90d",
    "sales_contacts_90d",
]

PASS_THRESHOLD = 0.9
WARN_THRESHOLD = 0.7


def _allowed_numbers(row: pd.Series, reason_codes_text: str) -> list[float]:
    """Any number that legitimately could appear in a draft for this account: the numbers
    already surfaced in its reason codes (which include both the account's value and the
    population median it's compared against) plus its raw feature values.
    """
    numbers = {float(n) for n in NUMBER_RE.findall(reason_codes_text)}
    for col in GROUNDING_FEATURE_COLUMNS:
        val = row.get(col)
        if pd.notna(val):
            numbers.add(float(val))
    return sorted(numbers)


def build_dataset(worklist: pd.DataFrame) -> MemoryDataset:
    # Empty drafts round-trip through CSV as NaN, not "" - fillna before filtering, or the
    # NaN float slips through as a "valid" 3-character string ("nan").
    draft_col = worklist["draft_outreach"].fillna("")
    drafted = worklist[draft_col.astype(str).str.len() > 0]
    samples = [
        Sample(
            input=row["draft_outreach"],
            target="",
            id=row["account_id"],
            metadata={"allowed_numbers": _allowed_numbers(row, str(row["reason_codes"]))},
        )
        for _, row in drafted.iterrows()
    ]
    return MemoryDataset(samples)


@solver
def replay_draft():
    """No model call — just replays the draft text the agent already generated so it can be
    scored, rather than asking Inspect to generate anything new.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.output = ModelOutput.from_content(model="replay", content=state.input_text)
        return state

    return solve


@scorer(metrics=[mean(), stderr()])
def numeric_groundedness():
    async def score(state: TaskState, target: Target) -> Score:
        draft = state.output.completion
        allowed = set(state.metadata.get("allowed_numbers", []))
        mentioned = {float(n) for n in NUMBER_RE.findall(draft)}
        if not mentioned:
            return Score(value=1.0, answer=draft, explanation="No numeric claims made.")
        grounded = {n for n in mentioned if any(abs(n - f) < 0.5 for f in allowed)}
        ungrounded = mentioned - grounded
        fraction = len(grounded) / len(mentioned)
        explanation = (
            "All numeric claims match this account's real data."
            if fraction == 1.0
            else f"Numbers in the draft not found in this account's data: {sorted(ungrounded)}"
        )
        return Score(value=fraction, answer=draft, explanation=explanation)

    return score


@task
def groundedness_eval(worklist_path: str = "agent/output/worklist.csv") -> Task:
    worklist = pd.read_csv(worklist_path)
    return Task(dataset=build_dataset(worklist), solver=replay_draft(), scorer=numeric_groundedness())


def run_groundedness_eval(worklist_path: str = "agent/output/worklist.csv") -> dict:
    """Runs the eval and returns a summary dict suitable for monitoring/latest_report.json."""
    worklist = pd.read_csv(worklist_path)
    dataset = build_dataset(worklist)
    if len(dataset) == 0:
        return {"status": "not_runnable", "reason": "No drafted accounts to evaluate."}

    logs = eval(
        Task(dataset=dataset, solver=replay_draft(), scorer=numeric_groundedness()),
        model="mockllm/model",  # unused - replay_draft() never calls generate()
        log_dir="monitoring/inspect_logs",
        display="none",
    )
    log = logs[0]
    scores = [s.scores["numeric_groundedness"].value for s in log.samples]
    flagged = [
        {
            "account_id": s.id,
            "value": s.scores["numeric_groundedness"].value,
            "explanation": s.scores["numeric_groundedness"].explanation,
        }
        for s in log.samples
        if s.scores["numeric_groundedness"].value < 1.0
    ]
    mean_score = sum(scores) / len(scores)
    worst_score = min(scores)
    status = "pass" if worst_score >= PASS_THRESHOLD else ("warn" if worst_score >= WARN_THRESHOLD else "fail")
    return {
        "status": status,
        "n_drafts_evaluated": len(dataset),
        "mean_groundedness": mean_score,
        "worst_groundedness": worst_score,
        "flagged_accounts": flagged,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_groundedness_eval(), indent=2, default=str))

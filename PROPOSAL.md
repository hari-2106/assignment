# Cordilla Account Scoring — Proposal

## Impact framing

**Who decides, and what changes.** Two people act on this model's output, split by
`account_type`: an **SDR** working cold outbound into `Prospect`/`Suspect` accounts, and an
**Account Manager** working win-back on `Former Customer` accounts. Today both are picking
which of thousands of untouched accounts to call this week with no ranking at all — first in
the list, most recently added, or whoever's top-of-mind. The model doesn't change *whether*
reps call accounts; it changes *which ones they call first*, and gives them a reason to open
the conversation with.

**What it's actually worth, grounded in the data.** I scored the 1,200-account training set
with the model and bucketed by predicted-probability decile, then looked at *actual*
`converted_within_90d` per decile (this is in-sample, not held-out validation — a real
lift estimate, not a rigorous one, and I'm flagging that explicitly rather than dressing it up):

| Decile | Avg. predicted P | Actual conversion rate |
|---|---|---|
| Bottom 10% | 4.0% | 1.7% |
| Top 10% (Hot tier) | 13.9% | **26.7%** |
| Overall / no ranking | — | 6.5% |

The top decile converts at **~4.1x** the base rate, and the bottom decile at roughly a
quarter of it. Applied to today's 300-account batch (30 Hot / 90 Warm / 180 Cold by the
agent's percentile tiers): if an SDR has bandwidth for, say, 30 calls this week, working the
Hot tier first should surface meaningfully more real conversions than working 30 accounts in
whatever order they're sitting in Salesforce today — for the same number of calls, not more
of them. That's the pitch to a VP of Sales: this doesn't ask for more headcount or more
activity, it makes the activity already happening land on better targets.

**Where I'm not going to overclaim.** Training data's blended base rate is 6.5% — notably
higher than the brief's own description of real-world cold-outreach conversion ("well under
1% for cold accounts, low single digits for anything with recent engagement"). That gap tells
me `training_data.csv` is not a random sample of Cordilla's full untouched-account universe;
it's likely a curated slice (accounts that had outcomes labeled or got worked historically).
So the *relative* lift (~4x) is the number I'd defend in the room — the *absolute* 26.7%
number should not be presented as "this is what Hot-tier accounts convert at in production."

**The cost of being wrong, in both directions.** A false positive (a Hot-tier account that
doesn't convert) costs one wasted call — cheap, self-correcting, reps notice quickly. A false
negative is quieter and more expensive: the bottom decile still converts at 1.7%, not zero.
Across the 180 Cold-tier accounts in today's batch, that implies a handful of real
conversions this ranking is deliberately deprioritizing. That's a real trade-off to say out
loud to a VP of Sales, not bury — the model doesn't eliminate that cost, it concentrates rep
effort where it pays off most on average, at the price of some accounts that would have
converted getting less attention.

## Agent design

**Framework: LangGraph.** This is fundamentally a pipeline with two genuine decision points,
not a multi-agent negotiation, so I didn't reach for CrewAI — its autonomy is harder to
justify precisely in a live walkthrough than an explicit state graph. The graph
(`agent/graph.py`): `load_inputs -> data_quality_gate -> [conditional: abort_and_alert |
score_accounts] -> segment_and_route -> generate_reason_codes -> [conditional: draft_outreach
| skip] -> write_outputs -> run_monitoring_checks`. Both conditionals are real business logic,
not decoration: the first refuses to score if input quality has collapsed wholesale (rather
than silently producing a confident-looking worklist from garbage — the exact failure mode
the brief calls out), and the second only invokes the one LLM step when there's a Hot-tier
account to draft for.

**Tools, and why each one exists.** `score_model_tool` wraps `.predict_proba` and nothing
else. `data_quality_tool` flags missing required fields, unparseable dates, and stale
snapshots (data up to 675 days old exists in this batch) without hiding flagged accounts —
they're still scored and shown, just marked `needs_review`. `reason_code_tool` is
deterministic: it ranks each account's top signals by (feature importance × distance from the
population median), using the model's real `feature_importances_` mapped to actual column
names (`intent_score` 0.271, `web_touchpoints_90d` 0.214, `sales_contacts_90d` 0.209 dominate;
`account_type`/`industry` contribute almost nothing). The one non-deterministic tool is
`draft_outreach`, isolated behind an `OutreachDrafter` interface specifically so a bad or slow
LLM call can never corrupt scoring, gating, or ranking — only the drafted blurb for capped
top-20 Hot accounts is affected. Its default backend is a documented mock (prompt, inputs,
model, and expected output shape specified in the docstring); if `GROQ_API_KEY` is set, the
same interface calls Groq's chat completion API for real instead — zero code changes needed
either way, and zero risk if it's absent during a live demo.

**Interface: Streamlit, not a chatbot.** The actual decision — "which accounts, in what
order, why" — is a ranked table, not a conversation. `agent/ui/app.py` gives reps a filterable
worklist plus a per-account detail view (reason codes, draft, a live "regenerate draft"
button) and a Monitoring tab surfacing the same health checks described below, so the person
using the output can also see whether it's currently trustworthy.

**Deployment (sketch, not built).** As a real service this would run on a daily/weekly
schedule (new accounts enter the funnel continuously), triggered by an orchestrator (Airflow/
a scheduled job) pulling fresh Salesforce data, writing the worklist back into Salesforce as a
custom field or list view SDRs already use, and pushing the monitoring report to wherever the
team already watches alerts (Slack/PagerDuty), not a dashboard nobody opens.

## Monitoring design

The brief's own cautionary tale is the design target: a model that keeps running, produces
output that looks fine, and quietly stops matching reality. Four checks, in
`monitoring/checks.py`:

1. **Input quality** — wraps the data-quality gate's dataset metrics: `intent_score` null
   rate compared against the ~40% baseline with tolerance (catches vendor coverage changes),
   missing-required-field rate, stale-snapshot rate. Runs every batch.
2. **Score-distribution drift (PSI)** — Population Stability Index between training-set and
   new-batch predicted probabilities. Thresholds: <0.10 stable, 0.10–0.20 warn, >0.20 fail.
   Today's batch: PSI ≈ 0.006, stable. Verified this actually fires by feeding it a
   synthetically shifted distribution (PSI 3.55 → fail) — it's not a check that always says OK.
3. **Tier-distribution sanity** — alerts if the Hot-tier share of a batch deviates >2x or
   <0.5x from the expected ~10%, catching threshold or upstream feature-pipeline breakage
   that a raw-score PSI check alone might miss.
4. **Business-outcome proxy** — precisely specified but honestly marked `not_runnable` today:
   comparing flagged accounts' real 90-day outcomes against predicted probability by decile is
   the *one* check that would have caught Cordilla's earlier drift, but this batch has no
   ground truth yet (scored 2026-08-01, outcomes land 90 days later). The function signature
   and exact logic are in the code now, ready to activate the first time real outcomes exist.

What tripping looks like in practice: PSI creeping from 0.02 to 0.15 over a few weeks with no
crash and no error — reps still get a worklist every Monday, it just quietly stops reflecting
what's actually converting. That's the alert that should page someone, not a dashboard nobody
checks until a VP asks why pipeline coverage looks off two quarters later.

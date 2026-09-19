# Cordilla Account Scoring — Proposal

## Impact framing

**Who decides, and what changes.** Two people act on this model's output, split by
`account_type`: an **SDR** working cold outbound into `Prospect`/`Suspect` accounts, and an
**Account Manager** working win-back on `Former Customer` accounts. Today both pick which of
thousands of untouched accounts to call this week with no ranking at all. The model doesn't
change *whether* reps call accounts; it changes *which ones they call first*, with a reason.

**What it's actually worth, grounded in the data.** I scored the 1,200-account training set
with the model and bucketed by predicted-probability decile, then looked at *actual*
`converted_within_90d` per decile (this is in-sample, not held-out validation — a real
lift estimate, not a rigorous one, and I'm flagging that explicitly rather than dressing it up):

| Decile | Avg. predicted P | Actual conversion rate |
|---|---|---|
| Bottom 10% | 4.0% | 1.7% |
| Top 10% (Hot tier) | 13.9% | **26.7%** |
| Overall / no ranking | — | 6.5% |

The top decile converts at **~4.1x** the base rate, the bottom decile at roughly a quarter of
it. Applied to today's batch (30 Hot / 90 Warm / 180 Cold): if an SDR has bandwidth for 30
calls this week, working the Hot tier first should surface meaningfully more real conversions
than working 30 accounts in whatever order they're sitting in Salesforce today — same number
of calls, not more of them. That's the pitch: no extra headcount, better-targeted activity.

**Where I'm not going to overclaim.** Training data's blended base rate (6.5%) is notably
higher than the brief's own description of real-world cold-outreach conversion ("well under
1% for cold accounts, low single digits for engaged ones"). That gap says `training_data.csv`
isn't a random sample of the full untouched-account universe — likely a curated slice. So the
*relative* lift (~4x) is what I'd defend in the room, not the absolute 26.7% figure.

**The cost of being wrong, in both directions.** A false positive (a Hot account that doesn't
convert) costs one wasted call — cheap, self-correcting. A false negative is quieter and more
expensive: the bottom decile still converts at 1.7%, not zero, so across 180 Cold-tier
accounts this ranking deliberately deprioritizes a handful of real conversions. Worth saying
out loud to a VP, not burying — the model concentrates effort where it pays off on average, at
the price of some accounts that would have converted getting less attention.

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

**Tools, and why each one exists.** `score_model_tool` wraps `.predict_proba`, nothing else.
`data_quality_tool` flags missing fields, unparseable dates, and stale snapshots (up to 675
days old in this batch) without hiding flagged accounts — still scored and shown, just marked
`needs_review`, and excluded from auto-drafted outreach (a real gap caught mid-build: two
Hot-tier accounts were getting confident drafts off 400+-day-old data before this fix).
`reason_code_tool` is deterministic: it ranks each account's top signals by (feature
importance × distance from the population median), using the model's real
`feature_importances_` mapped to real column names (`intent_score` 0.271,
`web_touchpoints_90d` 0.214, `sales_contacts_90d` 0.209 dominate; `account_type`/`industry`
contribute almost nothing). The one non-deterministic tool is `draft_outreach`, isolated
behind an `OutreachDrafter` interface so a bad LLM call can never corrupt scoring or ranking.
Default backend is a documented mock; if `GROQ_API_KEY` is set, the same interface calls
Groq's API for real instead — zero code changes either way, zero risk if absent during a demo.

**Interface: Streamlit, not a chatbot.** The actual decision — "which accounts, in what
order, why" — is a ranked table, not a conversation. `agent/ui/app.py` gives reps a filterable
worklist plus a per-account detail view (reason codes, draft, a live "regenerate draft"
button) and a Monitoring tab surfacing the same health checks described below, so the person
using the output can also see whether it's currently trustworthy.

**Deployment (sketch, not built).** As a real service this would run on a daily/weekly
schedule via a scheduled job pulling fresh Salesforce data, write the worklist back as a
Salesforce list view SDRs already use (not a second dashboard), and push the monitoring report
to wherever the team already watches alerts (Slack/PagerDuty).

## Monitoring design

The brief's own cautionary tale is the design target: a model that keeps running, looks fine,
and quietly stops matching reality. Five checks, in `monitoring/checks.py`:

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
   ground truth yet (scored 2026-08-01, outcomes land 90 days later). The logic is in the code
   now, ready to activate the first time real outcomes exist.
5. **LLM output groundedness** (via Inspect AI) — verifies every number the drafting step
   states about an account actually exists in that account's real data. The mock backend
   always passes by construction; this starts mattering the moment a real generative model is
   active and could invent or round a number. Verified it fires, not just passes, by feeding
   it a fabricated draft and watching the score drop.

What tripping looks like in practice: PSI creeping from 0.02 to 0.15 over a few weeks with no
crash and no error — reps still get a worklist every Monday, it just quietly stops reflecting
what's actually converting. That's the alert that should page someone, not a dashboard nobody
checks until a VP asks why pipeline coverage looks off two quarters later.

## What's missing, and what it would unlock

Two gaps limit this beyond a prototype. There's no contact-level data — these CSVs describe
accounts, not people, so a rep still can't act without a name/email joined in from Salesforce.
Once that exists, an LLM-with-tools research step (news, funding, leadership changes) could
turn "high intent score" into an actual conversation opener. Second, there's no invoice/
line-item data, so real RFM segmentation for Former Customer win-back isn't possible with what
we have (see `DOMAIN-DICTIONARY.md` section 5) — with it, tiering could weight by deal size,
not just conversion odds. Expanded visual version with charts and more ideas: `PROPOSAL.html`.

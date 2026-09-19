# Research Log

Kept live during the build, not written after the fact. Newest entries at the bottom.

---

## 2026-09-19 — Reading the brief, framing the problem

Read `Take-Home_Exercise_—_Candidate_Copy_(1).md`/`.pdf` and `README.md`. Key constraints
pulled out: don't retrain `model/model.pkl`, don't modify the CSVs, treat `2026-08-01` as
"today," mock any LLM call (a well-documented mock is judged the same as a live one), and the
three graded axes are impact framing, a real working agent, and monitoring for *quiet* failure
(the brief explicitly calls out a prior Cordilla scoring effort that looked good in testing and
then silently drifted out of sync with reality — that's the failure mode monitoring needs to
target, not "the model crashed").

**AI tool used:** Claude Code (Sonnet 5), interactive session.

**Prompt (paraphrased):** "explain in simple terms what is expected from us, save to
explanation.md; create CLAUDE.md with rules (don't retrain even if biased, commit every step,
log prompts in research log)."

**What came back / what I did with it:** Claude produced `explanation.md` (plain-language
summary of the brief) and an initial `CLAUDE.md` with the requested ground rules. Used both
mostly as-is — they matched the brief closely since it's a direct summarization task, low risk
of the model inventing requirements. No override needed here.

---

## 2026-09-19 — Deciding agent framework, UI, and LLM backend

**Prompt:** Asked Claude to discuss agentic orchestration options (I have experience in
LangGraph, CrewAI, LangChain), whether the user-facing surface should be a chatbot or a plain
Streamlit UI over the model, and whether to mock the LLM call or use a real Groq Cloud call for
better results; also asked it to help define the correct business persona/vertical case.

**What came back:** Claude recommended LangGraph over CrewAI (reasoning: CrewAI's
multi-agent autonomy is harder to defend precisely in a live Q&A than an explicit graph/state
machine, and the brief specifically asks to justify "the overall structure and control flow" —
a LangGraph graph is literally that). It recommended a Streamlit dashboard over a chatbot
(reasoning: the actual decision being made — "which accounts to call, in what order, why" — is
fundamentally a ranked table, not a conversation; a chatbot adds surface area without adding
decision value for this use case). It recommended building the LLM step as a documented mock
*and* an optional real Groq call behind the same interface, toggled by an env var, since the
brief states a mock is judged identically to a live call, so there's no grading upside to
depending on Groq being reachable during the live panel demo — but there is upside in demo
polish if it's there as a bonus, with zero downside if not.

**What I did with it / override:** Agreed with all three via AskUserQuestion (LangGraph,
Streamlit, Mock+optional Groq) — these matched my own instinct on the framework given I already
know LangGraph and CrewAI felt like overkill for what's really a linear pipeline with a couple
of real decision points, not a multi-agent negotiation. No override yet at this stage; will
record one below once something concrete produced a wrong/generic answer during implementation
(the assignment specifically asks for this, so it's tracked explicitly, not skipped).

---

## 2026-09-19 — Agent architecture plan

Used Claude Code's plan mode to design the concrete LangGraph graph before writing code —
persona split (SDR for Prospect/Suspect cold outbound vs. Account Manager for Former Customer
win-back), an explicit `data_quality_gate` node with a conditional "abort and alert" branch if
input quality collapses (rather than silently scoring garbage — directly modeled on the Cordilla
failure story), deterministic `reason_code` tool separate from the one LLM-backed
`draft_outreach` tool (isolating the only non-deterministic step), and monitoring checks
(input-quality, score-distribution PSI drift, tier-distribution sanity, plus an
honestly-labeled-as-not-runnable-today business-outcome-proxy check, since real conversion
outcomes for this batch don't exist yet). Plan reviewed and approved before any code was
written. Full plan saved at
`C:\Users\Prathamesh\.claude\plans\ancient-questing-elephant.md` for reference.

---

## 2026-09-19 — Data exploration findings (`scripts/explore_data.py`)

Ran the model and both CSVs through pandas to ground everything downstream in real numbers
instead of assertions.

**Model pipeline:** `ColumnTransformer` (OneHotEncoder on `account_type`+`industry`,
median-`SimpleImputer` on the 7 numeric columns, i.e. missing `intent_score` gets imputed to the
training median, not dropped) → `GradientBoostingClassifier` (40 estimators, depth 2, lr 0.05).
Mapped `feature_importances_` to real column names via
`model.named_steps['pre'].get_feature_names_out()` (don't trust raw index order — it's the
one-hot-expanded order, not the original 9 columns). Ranked importances:
`intent_score` 0.271, `web_touchpoints_90d` 0.214, `sales_contacts_90d` 0.209,
`employee_count` 0.111, `trial_started` 0.062, `trial_active_users` 0.048,
`mql_count_90d` 0.044 — `account_type`/`industry` dummies contribute almost nothing (<0.02
each). This directly drives the reason-code tool: only these top ~4-5 numeric features are
worth surfacing as "why."

**Training data (1200 rows):** overall conversion rate 6.5%, fairly flat across
`account_type` (Prospect 6.6%, Suspect 6.0%, Former Customer 7.2%) — account_type alone is a
weak signal, consistent with its near-zero feature importance. Conversion is meaningfully higher
where `intent_score` is present (8.2% vs 3.9% when missing), where `trial_started`=1 (9.9% vs
5.7%), and where `sales_contacts_90d`>0 (7.7% vs 4.7% cold). Note the overall 6.5% base rate is
noticeably higher than the brief's stated "well under 1% for cold accounts, low single digits
for engaged" — this training set is evidently not a uniform random sample of the full untouched
account universe (probably enriched toward accounts that got scored/labeled for some reason).
**Important caveat for the impact framing:** don't extrapolate this 6.5% rate onto the full
tens-of-thousands universe of untouched accounts without saying so explicitly.

**intent_score missingness:** ~40% null in both training (40.2%) and scoring batch (38.7%),
matching the brief. Checked whether missingness skews by company size (brief says real intent
vendors skew toward larger accounts) — in this dataset it doesn't: missingness is ~38-43% flat
across employee-count quartiles, and correlation between employee_count and intent_score is
~0.04 (basically none). So this synthetic dataset's missingness looks closer to random than the
real-world coverage-gap story the brief describes. Recorded as a caveat, not treated as
contradicting the brief — monitoring the null rate itself is still the right check regardless of
*why* it's missing.

**Score distribution:** predicted probabilities are heavily compressed — median ~5.2%, 90th
percentile ~10.9%, max ~27% (training) / ~21% (scoring batch). No account gets a high absolute
probability. This rules out fixed absolute-probability tier thresholds (e.g. "Hot = P>50%" would
select zero accounts) — tiers must be percentile-based against the observed distribution, e.g.
top ~10% of a batch = Hot. Train vs. scoring-batch decile-by-decile comparison is nearly
identical (means 0.0661 vs 0.0655) — no drift today, which gives a clean "stable" baseline for
the PSI drift check once implemented.

**snapshot_date staleness:** scoring batch snapshot ages (vs. 2026-08-01) range 0-675 days,
median 121 days. Some accounts are scored on data nearly two years old — worth a
staleness-based `needs_review` flag in the data-quality gate rather than treating all 300 rows
as equally fresh.

**AI tool used:** Claude Code, to write `scripts/explore_data.py` and the follow-up one-off
inspection snippet (feature-name mapping, size/missingness correlation). Verified the numbers
myself by reading the printed output rather than trusting a paraphrase.

---

## 2026-09-19 — Building the agent (tools, LLM client, graph, monitoring, UI)

Built in the order from the approved plan: `agent/tools.py` (deterministic scoring/gate/tier/
reason-code functions) → `agent/llm/client.py` (Mock/Groq drafter) → `monitoring/checks.py` →
`agent/graph.py` + `agent/run.py` (LangGraph wiring) → `agent/ui/app.py` (Streamlit). Each step
was smoke-tested against the real CSVs and model before committing, not just eyeballed.

**Where Claude Code got something concretely wrong, and what I changed:** the first version
of `draft_outreach` in `graph.py` capped Hot-tier drafts at `HOT_DRAFT_CAP` (20) by slicing
`tiers[tiers == "Hot"].index[:20]` — that takes the first 20 Hot accounts in whatever order
they happen to sit in the source CSV, not the top 20 by predicted probability. It ran without
error and produced a plausible-looking output, which is exactly the kind of silently-wrong
result that's easy to miss if you don't check output content against intent. Caught it by
actually reading the generated `worklist.csv` and asking "are these really the top 20," not
just "did it run." Fixed by sorting on `probability` (descending) before slicing:
`probability[tiers == "Hot"].sort_values(ascending=False).index[:HOT_DRAFT_CAP]`. Re-ran and
confirmed the drafted accounts are now the actual highest-probability Hot accounts.

**Other AI-assisted decisions in this pass, used mostly as generated:**
- Percentile-based tiering (`assign_tiers`) instead of absolute probability cutoffs — this
  followed directly from the score-distribution finding above (max ~27%, so any fixed
  threshold like ">50%" would select nobody), not a generic AI suggestion; verified by running
  it and checking the resulting tier counts (30/90/180) look sane before committing.
- The reason-code weighting (`importance x relative distance from median`) is a simple,
  explainable heuristic, not SHAP or anything rigorous — chose it deliberately over a
  "proper" explainability library given the brief's explicit statement that
  research-grade rigor isn't the bar here, and because it stays fast, dependency-free, and
  reliable even if the LLM step is down.
- PSI thresholds (0.10/0.20) for the drift check are the standard industry convention, not
  something invented for this exercise — used as-is, then verified they actually discriminate
  by testing against both the real (stable) data and a synthetic shifted distribution.

**AI tool used:** Claude Code (Sonnet 5), same interactive session, iterative build-test-commit
cycle for each file.

---

## 2026-09-19 — Consolidated raw material (to defend live)

Pulling together everything from above into one place — the numbers, hypotheses, and
assumptions I'd actually stand behind in the room, not a polished narrative.

**Model.** `sklearn.Pipeline`: OneHotEncoder(`account_type`, `industry`) + median-`SimpleImputer`
on 7 numeric columns → `GradientBoostingClassifier` (40 trees, depth 2, lr 0.05). Feature
importances (mapped to real names via `get_feature_names_out()`, not raw index order):
`intent_score` 0.271, `web_touchpoints_90d` 0.214, `sales_contacts_90d` 0.209,
`employee_count` 0.111, `trial_started` 0.062, `trial_active_users` 0.048,
`mql_count_90d` 0.044. `account_type`/`industry` contribute almost nothing (<0.02 each) —
if asked "does the model just re-derive account_type," the answer is no, it barely uses it.

**Base rates.** Training data (1,200 rows): 6.5% overall conversion, roughly flat across
account_type (6.0-7.2%). This is *higher* than the brief's stated real-world rates
(well under 1% cold, low single digits engaged) — training_data.csv is not a representative
random sample of the full untouched-account universe; treat it as a curated/labeled subset.
**Assumption I'm making explicit:** the *relative* lift the model provides should generalize
better than the *absolute* rates do.

**Lift number (the one to lead with).** Top predicted-probability decile converts at 26.7%
vs. 6.5% overall = **~4.1x lift**, computed in-sample on the 1,200-row training set (not a
held-out test — I'm calling that out proactively, not waiting to be asked). Bottom decile
converts at 1.7%, not zero — the honest "cost of being wrong" number: deprioritized accounts
still convert sometimes.

**Today's batch** (`data/accounts_to_score.csv`, 300 accounts, scored as of 2026-08-01):
30 Hot / 90 Warm / 180 Cold by percentile tiers (tiers must be percentile-based — predicted
probabilities top out around 20-27%, so any fixed cutoff like ">50%" selects zero accounts).
264 accounts route to the SDR track (Prospect/Suspect), 36 to the AM win-back track (Former
Customer). 0 rows hard-fail the data-quality gate; 38.7% have missing `intent_score`
(model-imputed, consistent with the ~40% baseline); 14% have snapshot data over a year old.
PSI between training and this batch's score distributions is ~0.006 — stable, no drift today.

**Hypotheses I did NOT get to validate and would say so if asked:** whether the ~40%
intent_score missingness in this synthetic data actually skews by company size the way the
brief describes real intent-vendor coverage doing (I checked — in this dataset it doesn't,
correlation ~0.04) — worth noting as a difference between this synthetic data and the
real-world data-sourcing story described in the brief, not a contradiction of it.

**What I'd change with more time:** wire `check_business_outcome_proxy` against real outcomes
once they exist; add a small backtest harness that replays historical batches through the
tiering logic to sanity-check the 4.1x number against something closer to held-out validation;
consider whether `employee_count`'s influence (0.111) should be capped so the model doesn't
implicitly under-prioritize genuinely promising small accounts.

---

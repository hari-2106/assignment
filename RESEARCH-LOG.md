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

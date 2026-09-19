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

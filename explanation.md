# What This Assignment Actually Wants — In Plain Terms

## The setup
Cordilla Systems (a B2B software company) has a Salesforce instance full of accounts —
some are paying customers, but most are Prospects, Suspects, and Former Customers that
nobody has touched. The VP of Sales says, vaguely, "do something with this data so reps
stop guessing which accounts to call." That's not a real spec — it's a mandate, and part
of the exercise is turning that vague ask into something concrete.

While digging in, we find a model someone already trained (`model/model.pkl`) that
predicts an account's likelihood of converting, plus the data it was trained on and a
fresh batch of 300 accounts to score. Nobody asked us to validate this model to research
standards — that's explicitly not the job. The job is: figure out roughly what this model
is worth if it works, build something that actually *acts* on its predictions, and design
a way to notice if it quietly goes wrong later without anyone watching.

There's a cautionary tale baked into the brief: an earlier scoring model at Cordilla
looked great in testing, shipped, and then silently drifted out of sync with reality over
a couple of quarters — nobody caught it because nobody was watching the right signal.
That failure mode (quiet, undetected drift — not a crash) is explicitly what the
monitoring piece is being graded against.

## The three things being evaluated
1. **Impact framing** — Can we explain, in terms a VP of Sales would care about (not
   "the model scores accounts" but real numbers), who acts on this model's output, what
   decision changes, and what's at stake if it's right vs. wrong. Must be grounded in the
   actual data (base rates, conversion rates, data coverage gaps), not made-up numbers.

2. **A working agent** — Not a design doc, an actual runnable thing. It loads the model,
   runs it against `data/accounts_to_score.csv`, and *does something* with the output that
   changes an SDR/AM's actual day (e.g., prioritizes accounts, drafts outreach, flags
   accounts for review, etc.). We choose the shape, the tools it has, the framework (or
   no framework), and justify why. If it needs to call an LLM as part of its reasoning,
   that call can be **mocked** (clearly documented stand-in), since no real LLM API key is
   provided — but the mock's prompt/inputs/tools/expected output must be well-specified.

3. **Monitoring** — Real, concrete detection design for the "quiet failure" mode: things
   like data drift, missing/degraded input coverage, prediction distribution shifts, or
   business-outcome mismatches. At least one piece must be concrete enough to actually
   implement (real code, pseudocode, or a precisely specified check) — not just "we should
   add logging."

## Deliverables (must all exist in the repo)
- `agent/` — the working agent code
- `monitoring/` — at least one concrete monitoring check (or folded into `agent/`)
- `PROPOSAL.md` (~800–1200 words) — impact framing + agent design rationale + monitoring
  design, all in one place
- `RESEARCH-LOG.md` — a *running* log kept as we go: hypotheses, data observations, dead
  ends, and literally what we asked our AI tool and what it returned, including at least
  one moment where we corrected/overrode a wrong or generic AI answer. Not written after
  the fact.
- Real, incremental git history — commit as we go, not one final squash commit.

## Constraints / things we explicitly do NOT do
- Don't retrain, tune, or re-validate the model to research rigor.
- Don't modify or regenerate the provided CSVs.
- Don't build a full production deployment pipeline (a sketch in the proposal is enough).
- Don't get a real LLM API call working — mock it, clearly.
- Don't handle every data edge case — just the ones that matter for impact/monitoring.
- No requirement for a formal architecture diagram, presentation, or test suite.

## What happens after submission
We push the repo publicly and send the link — that's the whole submission. Later, in a
live follow-up presentation (20–25 min), we walk through the proposal, run the agent live,
and the panel will throw a live curveball (new constraint, missing data source, stakeholder
objection) to see how our reasoning and code hold up in the moment.

## Time-box
Suggested ~4 hours of work, hard 24-hour deadline. Going over 4 hours is allowed but the
bar is "ship something real and be honest about its limits," not polish.

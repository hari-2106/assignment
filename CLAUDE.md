# Working Rules for This Repo (Cordilla Account Scoring Take-Home)

These rules apply to any AI assistant (Claude Code or otherwise) working in this repo for
the duration of this take-home exercise.

## Hard constraints from the assignment
- **Never retrain, fine-tune, or re-fit `model/model.pkl`.** Load it and call
  `.predict_proba()` only. If it looks biased or wrong, note that in `PROPOSAL.md` /
  `RESEARCH-LOG.md` — do not "fix" it by retraining.
- **Never modify or regenerate `data/training_data.csv` or `data/accounts_to_score.csv`.**
  Read-only, always.
- Treat `2026-08-01` as "today" for any recency/age calculations involving this data —
  never the system clock.
- No real LLM API calls. Any LLM-in-the-loop step in the agent must be a clearly labeled
  **mock** with documented prompt, inputs, available tools, and expected output shape —
  judged the same as a real call, so make it specific, not hand-wavy.
- Keep it a rough, real prototype — no formal test suite, no CI/CD, no production
  packaging effort. Working and readable beats polished.

## Working process
- **Commit every meaningful step**, not one commit at the end. Small, real, incremental
  commits that reflect actual progress (data exploration → impact framing → agent →
  monitoring → proposal), so the git history itself tells the story of how this was built.
- **Log prompts as we go, not after the fact.** Every non-trivial AI prompt/response
  exchange used to build this repo gets logged in `RESEARCH-LOG.md` in real time —
  what was asked, what came back, whether it was used as-is, and if not, what was changed
  and why. Write the log entry in the same work session as the exchange, not retroactively
  at the end.
- **Explicitly record at least one place an AI suggestion was wrong, generic, or overridden**,
  and what was substituted instead — this is a required part of `RESEARCH-LOG.md`, not
  optional color.
- Don't write a summary/presentation version of the findings anywhere except the final
  `RESEARCH-LOG.md` entry, which should consolidate the raw material (numbers, hypotheses,
  assumptions) to stand behind live — not a polished narrative.

## Scope discipline
- Don't over-engineer the agent framework choice, deployment story, or monitoring stack —
  a justified, working, minimal version is worth more here than a comprehensive one.
- Don't audit the model to research-grade statistical rigor — enough data inspection to
  ground the impact framing and monitoring design is the bar, not more.
- Flag data-quality issues only where they matter to impact framing or monitoring; don't
  chase every edge case.

## Practical notes learned while building
- Run the agent as `python -m agent.run` from the repo root, never `python agent/run.py` —
  the latter breaks the `agent.*` package import because Python doesn't add the repo root to
  `sys.path` when a script is run by relative path.
- The model's predicted probabilities are heavily compressed (roughly 3.5%-27%, median ~5%).
  Any future tiering/thresholding logic must use percentiles of the batch's own score
  distribution, never a fixed absolute cutoff.
- Prefer plain ASCII punctuation (`-` not em dash) in any string that might be printed to a
  Windows terminal — em dashes render as replacement characters (`ï¿½`) in this environment's
  default codepage. Not an issue in the Streamlit UI (browser renders UTF-8 fine), only in
  console output/logs.

## Model bias / trust caveat (explicit ground rule)
- We are aware the model may carry biases inherited from historical/partial data (e.g.,
  intent data skew toward larger accounts, missing values, low base rates). **We do not
  retrain or attempt to statistically correct the model to address this.** Any concerns
  about bias or drift get surfaced as monitoring signals and caveats in the proposal, not
  as silent code changes to the model.

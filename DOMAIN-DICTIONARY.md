# Cordilla Account Scoring: Domain Dictionary

This reference explains the sales, data, AI, monitoring, and delivery terminology in the take-home exercise, defines every CSV column, and adds useful sales concepts such as RFM. It is a learning reference, not an additional assignment requirement.

## 1. Context and interpretation

**The business problem:** Cordilla Systems, a roughly 900-person business-to-business software company, has many accounts in Salesforce that sales representatives rarely contact. An existing model estimates conversion likelihood. The assignment is to turn those scores into useful sales actions, estimate their business impact, and detect when the system becomes unreliable.

**Sources of meaning:** The exercise and README establish project facts. Observations below come from the supplied CSVs. Where the source does not define an operational rule, this dictionary explicitly marks it as an interpretation or an open question. The extra glossary sections explain general concepts; they do not imply those capabilities or data exist in this project.

**Time reference:** Use **2026-08-01** as today. The files were generated as of that date, but their individual `snapshot_date` values vary. A file generation date, an account snapshot date, a last-activity date, and a purchase date are different things.

## 2. Data dictionary: every column

CSV means **comma-separated values**: a tabular file with column names in its first row. Here each row describes an account. Training has 12 columns; the scoring file has the same columns except the conversion label.

### Identifiers and context

| Column | Type and example | Meaning and role | Interpretation limits |
|---|---|---|---|
| `account_id` | Text; `ACC-00002` | Identifier for the account represented by the row. Use it to associate scores and actions with an account. | It is an identifier, not a model feature. Do not infer account quality, age, or order of acquisition from the numeric suffix. |
| `account_type` | Category; `Prospect`, `Suspect`, `Former Customer` | Account relationship/status category; one of the nine model features. Broadly, a suspect is a possible buyer, a prospect is a potential buyer with some qualification or interest, and a former customer previously purchased. | Exact criteria for these categories are not supplied. A prospect is not automatically an SQL or an open opportunity. |
| `snapshot_date` | Date, `YYYY-MM-DD`; `2026-07-07` | Date associated with the account snapshot. Can support an age/freshness check relative to 2026-08-01. Not a model input according to the README. | Treating it as the feature observation date is a working interpretation. Confirm when the features were measured and where the 90-day windows begin/end. It is not documented as the last contact or purchase date. |
| `employee_count` | Integer; `21` | Number of employees associated with the account's company; a firmographic size feature. | Whether this includes subsidiaries, contractors, or only one location is unspecified. It is not the number of paid product seats or a revenue amount. |
| `industry` | Category; `Retail` | Business sector of the account; a model feature. | Both files contain Retail, Professional Services, Financial Services, Manufacturing, Software, and Healthcare. Classification rules are unspecified. |

### Intent, engagement, and outreach

| Column | Type and example | Meaning and role | Interpretation limits |
|---|---|---|---|
| `intent_score` | Decimal or blank; `30.9` | A score representing buying-interest signals; the exercise associates intent data with partial vendor coverage. A model feature. | Higher values conventionally indicate stronger intent, but the vendor's scale and exact definition are not given. Do not assert a documented 0–100 scale. A blank means unavailable, not zero interest. It is not a probability. |
| `mql_count_90d` | Nonnegative integer; `2` | Interpreted as the number of marketing-qualified leads associated with the account during a 90-day lookback. A model feature. | The exact MQL qualification rule, whether the count is unique people or qualification events, and the lookback anchor are unspecified. It does not necessarily count buyers or opportunities. |
| `trial_started` | Binary integer; `1` or `0` | Indicator that a trial has been started: `1` = yes, `0` = no. A model feature. | The trial's start date and the indicator's observation window are not supplied. `1` does not by itself mean that the trial is currently running. |
| `trial_active_users` | Nonnegative integer; `1` | Count of active users associated with the account's trial; a product-usage feature. | The activity definition and time window are unspecified. Zero can indicate no trial or a trial without active users; interpret with `trial_started`. It is not a count of paying customers. |
| `web_touchpoints_90d` | Nonnegative integer; `9` | Interpreted as recorded web-related interactions associated with the account during a 90-day lookback. A model feature. | Whether a touchpoint is a visit, page view, form submission, ad interaction, or deduplicated event is unspecified. It need not represent a distinct person. |
| `sales_contacts_90d` | Nonnegative integer; `4` | Interpreted as the number of sales contact/outreach interactions associated with the account during a 90-day lookback. A model feature. | Confirm whether this counts attempts, completed conversations, or unique contacts. It does not prove that four people replied or four meetings occurred. |

### Outcome / target

| Column | Type and example | Meaning and role | Interpretation limits |
|---|---|---|---|
| `converted_within_90d` | Binary integer; `0` or `1` | Historical target label: `1` records a conversion within the defined 90-day outcome window; `0` records no conversion. Present only in `training_data.csv`. | The exact conversion event and window anchor are unspecified. Becoming a paying customer is a plausible business interpretation, not a confirmed label definition. Confirm full follow-up before interpreting `0` as a mature negative. Never use this target as an input feature. |

**Suffix `90d`:** 90 days. Activity columns conventionally describe a backward-looking window, while the target describes a forward-looking outcome window. These directions are reasonable interpretations; the source does not fully specify the measurement contract.

**Model input order documented in the README:** `account_type`, `employee_count`, `industry`, `intent_score`, `mql_count_90d`, `trial_started`, `trial_active_users`, `web_touchpoints_90d`, `sales_contacts_90d`.

### Observed values in the supplied files

These are observed ranges, not guaranteed allowable limits or proposed validation thresholds.

| Property | Training file | Scoring file |
|---|---:|---:|
| Rows | 1,200 | 300 |
| Prospects | 632 | 163 |
| Suspects | 402 | 101 |
| Former customers | 166 | 36 |
| Snapshot date range | 2024-08-20 to 2026-07-31 | 2024-09-25 to 2026-08-01 |
| Employee count range | 3–4,429 | 5–1,909 |
| Missing intent scores | 482 / 1,200 = 40.17% | 116 / 300 = 38.67% |
| Nonmissing intent score range | 1.5–83.3 | 1.7–77.5 |
| MQL count range | 0–9 | 0–6 |
| Trial started = 1 | 223 | 50 |
| Trial active user range | 0–8 | 0–5 |
| Web touchpoint range | 0–15 | 0–14 |
| Sales contact range | 0–9 | 0–9 |
| Positive conversion labels | 78 / 1,200 = 6.5% | Not provided |
| Negative conversion labels | 1,122 | Not provided |

Only `intent_score` has blank cells in these files. No account IDs are shared between the two files. Neither observation establishes that the data are correct or representative of deployment.

The historical **6.5% label rate** is a property of this training sample. It is not a validated forecast for the scoring population, not a model accuracy score, and not evidence that outreach causes a 6.5% conversion rate. The exercise separately describes cold-account outreach-to-conversion rates as well under 1% and rates for engaged accounts as low single digits; populations and denominators must be reconciled before making an impact claim.

### Example: reading one actual row

`ACC-00002` is a Suspect in Retail with 21 employees and snapshot date 2026-07-07. Intent is unavailable. It has 2 recorded MQLs, a trial-start indicator of 1, 1 active trial user, 9 web touchpoints, 4 sales contacts, and a conversion label of 0. Its snapshot is 25 days old relative to the exercise date.

This describes recorded signals. It does not establish that the account last engaged 25 days ago, that 4 outreach attempts received replies, or that no future conversion is possible.

## 3. Sales and customer terminology from the exercise

| Term | Plain-language meaning | Relevance here |
|---|---|---|
| B2B | Business-to-business: selling to organizations. | The account is a company, often involving several people in a purchase. |
| Workflow software | Software that coordinates repeatable business tasks and processes. | Cordilla's product category; specific product capabilities are not supplied. |
| Account | A company or customer organization tracked for commercial activity. | The unit being scored. |
| Paying customer | An account that purchases the service. | Distinct from the non-customer population targeted in the exercise. |
| Non-customer | An account not currently paying. | Includes prospects, suspects, and former customers here. |
| Prospect | A potential customer with some assessed suitability or interest. | Local qualification criteria must be established. |
| Suspect | An account that might be a buyer but is not yet sufficiently qualified. | May require research or qualification before outreach. |
| Former customer | An account that previously bought but is no longer a customer. | May need a win-back approach and an understanding of why it left. |
| CRM | Customer relationship management; also the system used to manage customer and sales records. | Salesforce is the CRM named in the exercise. |
| Salesforce instance | The organization's configured Salesforce environment. | Holds account records and potentially leads, contacts, activities, and opportunities. |
| Sales representative / rep | A person who works with potential or existing buyers to generate sales. | Receives the prioritized actions. |
| SDR | Sales development representative: qualifies potential buyers and creates opportunities for further sales work. | A likely user of an account worklist. Role boundaries vary by company. |
| Account manager / AM | Person responsible for an ongoing commercial relationship, often including retention and expansion. | Another possible user of the agent. |
| VP of Sales | Senior leader accountable for sales execution and results. | Needs a credible account of impact and tradeoffs. |
| Outreach | Proactive contact through channels such as calls or email. | An action that consumes rep time; it is not itself a conversion. |
| Cold account | An account with little or no recent relationship or engagement. | The brief describes very low outreach conversion rates for this population. |
| Engagement | Observable interaction with marketing, sales, or the product. | Trial use, MQLs, and web activity can provide different signals. |
| Conversion | Completion of a defined business event. | Define whether this means paid purchase, opportunity creation, or another milestone before calculating value. |
| Conversion rate | Conversions divided by eligible units in a specified population and period. | Specify whether the denominator is accounts contacted, all accounts scored, or something else. |
| Account scoring | Assigning a numeric estimate or ranking to an account. | Helps decide where to spend limited attention. |
| Buying intent | Evidence suggesting that an organization may be researching or considering a purchase. | Vendor intent is incomplete and skews toward larger accounts in the scenario. |
| MQL | Marketing-qualified lead: a lead meeting agreed marketing criteria for relevance or engagement. | Qualification is organization-specific; MQL does not mean closed sale. |
| Trial | A limited opportunity to evaluate a product before purchasing. | Its availability and use can distinguish accounts with direct product experience. |
| Active user | A user who meets a defined activity criterion in a stated period. | The definition is missing for the supplied trial count. |
| Touchpoint | A recorded interaction between a potential customer and the company. | Multiple touchpoints may belong to the same person or session. |
| Coverage gap | Absence of data for part of the relevant population. | Missing intent must not be interpreted as lack of interest. |
| Marketing automation platform | Software for managing campaigns, nurturing, and tracking marketing responses. | A possible source of MQL and engagement signals. |
| Third-party intent vendor | An external provider of signals about purchase-related research. | Coverage and scoring rules can change independently of Cordilla. |
| Firmographics | Company attributes such as size, industry, and location. | Employee count and industry are available examples. |
| Technographics | Information about technologies a company uses. | Mentioned as a potential enrichment source but not present in these CSVs. |
| Enrichment | Adding or refreshing information about an existing record. | Can improve context while introducing vendor dependencies and coverage bias. |
| Attribution | Rules for assigning credit for an outcome to prior interactions. | A recorded web/ad interaction does not establish that it caused a sale. |
| Product usage telemetry | Events or measurements recorded by the product about usage. | Provides trial activity signals for accounts that have trials. |

CRM object distinctions and sales terminology can be cross-checked against the [Salesforce glossary](https://help.salesforce.com/s/articleView?id=glossary.htm&language=en_US&type=0) and [Salesforce sales terminology guide](https://www.salesforce.com/blog/sales/sales-terms/). Operational definitions must still be agreed locally.

## 4. Additional sales concepts

These terms extend beyond the exercise and help explain a practical sales workflow.

| Term | Meaning | Example or application |
|---|---|---|
| Lead | A potential buyer or inquiry that has not yet completed the company's qualification process. | One company can be associated with several leads. |
| Contact | An identifiable person associated with a business relationship. | Different from a contact attempt counted as an activity. |
| SQL | Sales-qualified lead: a lead sales has assessed as suitable for a sales conversation or further pursuit. | MQL-to-SQL conversion measures one handoff, not final sales. |
| SAL | Sales-accepted lead: a lead accepted by sales for follow-up. | An optional lifecycle stage between marketing qualification and sales qualification. |
| PQL | Product-qualified lead: a potential buyer qualifying through meaningful product usage. | Trial usage could contribute if explicit criteria are defined. |
| Opportunity | A qualified potential deal tracked through sales stages. | It may have an amount, expected close date, and owner. |
| Closed won / closed lost | A deal recorded as successfully sold / unsuccessfully concluded. | Different outcomes from an unanswered outreach attempt. |
| AE | Account executive: a seller often responsible for managing qualified deals through closing. | May receive opportunities from SDRs. |
| BDR | Business development representative: a role often focused on finding and qualifying new business. | The division between BDR and SDR varies by organization. |
| RevOps | Revenue operations: coordination of revenue data, systems, processes, and measurement. | Could own CRM definitions and workflow reliability. |
| ICP | Ideal customer profile: characteristics of organizations well suited to the product. | Firmographics can indicate fit, but company size alone is not an ICP. |
| Buyer persona | A description of a relevant individual role, needs, and motivations. | A buyer persona describes a person; an ICP describes a company. |
| Buying committee | The people influencing or approving a B2B purchase. | A user, technical evaluator, finance approver, and decision-maker may differ. |
| ABM / account-based marketing | Coordinated marketing directed at selected accounts. | Could use account tiers to allocate research and campaign effort. |
| Account-based selling | Coordinated sales activity focused on the needs and stakeholders of an account. | Useful when one account has multiple leads or contacts. |
| Inbound / outbound | Buyer-initiated interest / seller-initiated prospecting. | A requested demo and a cold email have different baseline conversion rates. |
| Qualification | Assessing whether a buyer and opportunity warrant further sales investment. | Check fit, need, timing, and ability to buy. |
| BANT | Budget, Authority, Need, Timeline; a qualification framework. | The supplied CSVs do not contain these four dimensions. |
| Discovery | Conversation or research to understand the buyer's problem and buying process. | A model score can prioritize discovery but cannot replace it. |
| Nurturing | Continued relevant communication until an account is ready for sales engagement. | A lower-priority account need not be permanently discarded. |
| Cadence / sequence | A scheduled series of outreach steps. | Calls and emails spaced over an agreed period. |
| Next-best action | The most appropriate next step given available information and constraints. | Research, call, nurture, or request human review. |
| Routing | Assigning an account or task to the appropriate owner/team. | Consider territory and existing ownership as well as score. |
| Worklist / queue | An ordered set of accounts or tasks awaiting action. | A concrete agent output that changes a rep's day. |
| Tier | A grouping used to prioritize service or effort. | High, medium, and low priority require explicit rules. |
| Suppression | Excluding an account/contact from a particular action. | Respect existing ownership, opt-outs, or recent contact policy where those data exist. |
| Win-back / reactivation | Attempts to regain a former customer's business. | Requires different context from first-time acquisition. |
| Churn | Loss of customers or recurring revenue over a defined period. | Former customer status alone does not provide a churn date or reason. |
| Retention | Keeping customers or revenue across a period. | Requires customer status or revenue observations over time. |
| Upsell / cross-sell | Selling more of an existing offering / an additional offering. | Neither is directly measured by the supplied conversion label. |
| Sales pipeline | The set of active potential deals and their stages. | Avoid confusing it with an ML processing pipeline. |
| Sales funnel | Aggregate progression through stages, often shown as counts and conversion rates. | Accounts → contacted → qualified → opportunities → customers. |
| Sales cycle | Time from a defined sales starting point to a deal outcome. | A 90-day label may not capture a longer enterprise buying cycle. |
| Win rate | Won opportunities divided by a defined opportunity denominator. | State whether the denominator is closed opportunities or all created opportunities. |
| Quota | Sales target assigned to a person or team for a period. | Can shape incentives and behavior around account selection. |
| Capacity | The amount of work a team can perform in a period. | Prioritization should account for how many accounts reps can meaningfully work. |
| SLA | Service-level agreement: an agreed response or service commitment. | Example: follow up on a qualified inbound request within an agreed time. |
| GTM | Go-to-market: how a business reaches, sells to, and serves its market. | Account prioritization is one part of this larger system. |

## 5. RFM: Recency, Frequency, Monetary value

**RFM** is a customer segmentation approach based on transaction history: how recently a customer bought, how often they bought, and how much they spent. It is a segmentation method, not automatically a predictive conversion model. See [IBM's RFM overview](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=marketing-rfm-analysis).

| Component | Definition | Example calculation |
|---|---|---|
| Recency (R) | Time since the most recent qualifying purchase. | `analysis_date - last_purchase_date`, in days. |
| Frequency (F) | Number of qualifying purchases in a specified window. | Count paid orders during the last 12 months. |
| Monetary value (M) | Qualifying spend in a specified window. | Sum net purchase amounts during the same 12 months. |

### Illustrative scoring example

The following numbers and segments are invented examples, not supplied Cordilla data or universal cutoffs.

| Customer | Days since last purchase | Purchases in 12 months | Net spend in 12 months | Possible interpretation |
|---|---:|---:|---:|---|
| A | 10 | 12 | $24,000 | Recent, frequent, high-spend customer. |
| B | 180 | 10 | $20,000 | Historically valuable customer whose lack of recent purchases merits investigation. |
| C | 5 | 1 | $300 | Recent new buyer with limited purchase history. |

A possible scheme assigns each dimension a score from 1 to 5. Fewer days since purchase receives a higher R score; higher purchase frequency and spend receive higher F and M scores. A code such as `555` denotes three high scores under that scheme, not a 555% probability. Choose bins and any combined weighting for the business and document tie handling. Recurring subscription invoices can make frequency largely reflect billing cadence, so subscription businesses need an explicit definition of a meaningful transaction.

### Can we compute RFM from the supplied CSVs?

**True purchase-based RFM cannot be computed from these files.**

| Needed for RFM | Available here? | Why a nearby column is insufficient |
|---|---|---|
| Last purchase date | No | `snapshot_date` measures the record's date, not purchase recency. |
| Purchase count/history | No | MQLs, web touchpoints, and sales contacts are activity counts, not purchases. |
| Transaction amounts or net spend | No | `employee_count` is company size; it is not monetary value. |

To add RFM, obtain account-linked transaction IDs, purchase dates, and amounts, plus currency and cancellation/refund rules. Define the analysis date and window. For former customers, purchase history may be useful for win-back segmentation. For suspects and never-purchased prospects, purchase-based RFM provides little differentiation.

**Optional engagement segmentation:** The activity counts could support an explicitly named engagement segmentation. Genuine engagement recency would still require a last-activity timestamp. Snapshot age may support a separate freshness check, but should not be relabeled engagement recency. Do not present an engagement proxy as standard RFM.

## 6. Impact and commercial metrics

These general definitions help connect a score to a decision. Monetary examples and formulas are illustrative; the CSVs contain no prices, revenue, margins, or outreach costs.

| Term | Meaning / formula | Important distinction |
|---|---|---|
| Impact framing | Explaining who changes which decision, what improves, and what errors cost. | Start with the rep's allocation of time and the business outcome. |
| Baseline | The reference against which a change is compared. | Current rep selection or random eligible selection can be baselines. |
| Base rate | Outcome prevalence in a specified population. | Training prevalence is not necessarily deployment prevalence. |
| False positive | A negative case incorrectly selected or predicted positive. | At an action threshold, it can waste rep time; a high probability is not a guarantee. |
| False negative | A positive case incorrectly rejected or predicted negative. | A worthwhile account may miss timely attention. |
| Opportunity cost | Value of the best alternative forgone when using scarce resources. | Calling one account may mean not calling another. |
| Incrementality | Additional outcomes caused by an intervention compared with its absence. | High conversion propensity is not evidence of outreach impact. |
| Uplift / treatment effect | Difference in outcome probability under one action versus another. | Requires causal evidence or explicit assumptions. The supplied classifier does not establish this. |
| Expected value | Probability-weighted outcome value, adjusted for relevant costs. | Under strong assumptions: incremental conversion probability × contribution per conversion − incremental action cost. |
| ROI | Return on investment: `(incremental benefit - cost) / cost`, using consistent units. | State the period, attribution assumptions, and what counts as benefit and cost. |
| ACV | Annual contract value: annualized value of a contract under the chosen accounting definition. | Not necessarily profit or lifetime value. |
| MRR / ARR | Monthly / annual recurring revenue; ARR is often 12 × MRR for a consistent recurring base. | Exclude one-time charges under the chosen definition. |
| TCV | Total contract value across the full contract term and included charges. | A multiyear contract's TCV differs from its annual value. |
| CAC | Customer acquisition cost: included acquisition spending divided by acquired customers. | Define costs, cohort, and attribution period consistently. |
| LTV / CLV | Lifetime customer value: expected economic contribution from the relationship. | Requires retention, margin, and time assumptions; not available from employee count. |
| Gross margin | `(revenue - cost of goods/services sold) / revenue`. | Revenue gains are not the same as profit gains. |
| KPI | Key performance indicator tied to an objective. | Meetings alone may be a weak proxy for incremental revenue. |
| Proxy metric | An available measure standing in for the desired outcome. | Replies or meetings can arrive before 90-day conversion outcomes. |
| Leading / lagging indicator | An early signal / a later outcome measure. | Data freshness can change before measured conversions decline. |

**Illustrative arithmetic:** If 100 additional contacts caused 0.5 percentage points of conversion uplift, the expected additional conversions would be `100 × 0.005 = 0.5`. At an assumed $2,000 contribution per conversion and $300 total incremental contact cost, expected net contribution would be `$1,000 - $300 = $700`. These assumptions are invented to demonstrate units; no such uplift or contribution is established by the supplied data.

## 7. Model, data science, and evaluation terminology

| Term | Meaning and application |
|---|---|
| AI / artificial intelligence | Broad category of systems performing tasks associated with intelligent behavior; includes classifiers and language models. |
| ML / machine learning | Learning patterns from data to make predictions or decisions. |
| Model | A learned mapping from inputs to outputs; here an existing conversion classifier. |
| Feature / model input | A variable used to produce a prediction, such as employee count. |
| Target / label | The outcome used during supervised training, here `converted_within_90d`. |
| Labeled / unlabeled data | Records with / without known target outcomes. Unlabeled does not mean negative. |
| Historical / training data | Past examples used to fit the model. These 1,200 rows are not an independent test set. |
| Batch scoring / inference | Applying the already-trained model to multiple records, here the 300 scoring accounts. |
| Prediction horizon | Future period over which an outcome is assessed; the label names 90 days. |
| scikit-learn | Python machine-learning library used for the supplied model pipeline. |
| ML pipeline | A sequence of preprocessing and estimation steps executed together. Different from a sales pipeline. |
| Fit / train | Estimate a model's parameters from data. The supplied model is already fitted. |
| Retraining / tuning | Fitting again with data / adjusting model choices or hyperparameters. The exercise explicitly excludes this work. |
| `.predict_proba()` | Method returning class probability estimates. Identify the positive-class column using the model's class labels; do not assume column meaning without checking. |
| Propensity score | In this business setting, an estimated likelihood of conversion. This usage differs from the treatment-assignment propensity score in causal inference. |
| Probability calibration | Agreement between predicted probabilities and observed frequencies over comparable cases. A score of 0.8 is not automatically a reliable 80% conversion likelihood. |
| Ranking | Ordering accounts by a score or rule; good ranking does not imply calibrated probabilities. |
| Threshold | Cutoff used to select an action or predicted class. Its consequences depend on rep capacity and error costs. |
| Precision / precision@K | Fraction of selected cases that are positive / fraction of the top K ranked cases that are positive, once outcomes are known. |
| Recall | Fraction of all actual positives captured by the selected group. |
| Lift@K | Top-K positive rate divided by the overall positive rate in the same evaluation population. Ranking lift is not causal uplift. |
| Accuracy | Fraction of correct class predictions at a specified threshold. With rare positives, predicting mostly negatives can look accurate but be unhelpful. |
| Class imbalance | A large difference between positive and negative counts. Here training contains 78 positives and 1,122 negatives. |
| Cross-validation | Repeated train/validation splitting to estimate model performance. The exercise does not require it. |
| Holdout / out-of-sample evaluation | Evaluation on records not used in fitting or model selection. Re-scoring training data does not provide this. |
| Overfitting | Learning training-specific patterns that do not generalize well. |
| Data leakage | Using information unavailable at the intended prediction time, or allowing evaluation information into training. |
| Selection bias | Distortion from how examples enter a dataset. Historically contacted accounts may differ from untouched accounts. |
| Missingness / imputation | Absence of values / substitution of a chosen value or estimate during preprocessing. Missing intent should not silently become a business claim of no interest. |
| Cohort / segment | A group sharing a relevant property or observation period. Monitor prospects, suspects, and former customers separately where useful. |
| Label maturity | Whether sufficient follow-up has passed to observe the full outcome window. |
| Right censoring | Incomplete outcome observation because follow-up ends before the relevant horizon. Recent negative labels deserve clarification. |
| Correlation / causation | Association between variables / one factor producing a change in another. More sales contacts and more conversions need not mean that extra contacts caused those conversions. |
| Hypothesis / assumption | A claim to investigate / a premise provisionally used in reasoning. Record both explicitly rather than presenting them as findings. |

## 8. Agent and implementation terminology

| Term | Meaning and application |
|---|---|
| Agent | A system that uses inputs and available tools/actions to carry out a task. Here it must turn model output into a useful, runnable workflow. |
| Tool / action | A callable capability such as scoring data, checking quality, drafting outreach, or creating a task. |
| Control flow | Rules determining which step runs next, including branches, review paths, and failures. |
| Agent framework | A library for organizing agent state, tool use, and execution. The exercise allows a framework or a justified simpler implementation. |
| Deterministic rule | A rule producing the same output for the same inputs. Useful for validation, eligibility, and routing constraints. |
| LLM | Large language model; can generate or interpret text. It is distinct from the trained conversion-scoring model. |
| Prompt / instruction | Directions and context supplied to a language model. |
| Mock / stand-in | A deliberate substitute for an external model/tool call. It should preserve a clearly documented interface. |
| API / API key | Application programming interface / credential used to authenticate access. No LLM key is provided by the exercise. |
| Tool contract | Defined inputs, outputs, and permitted behavior for a tool. Makes a mock replaceable and failures interpretable. |
| Human review | A step requiring a person to assess a proposed action or uncertain case. |
| Reason code | A concise explanation of a rule or observed signal behind a decision. It is not automatically a causal model explanation. |
| Guardrail | A constraint that limits an action, such as blocking incomplete records from automatic outreach. |
| Idempotency | Repeating the same operation without unintended duplicate effects, such as duplicate CRM tasks. |
| Audit trail | A record of inputs, decisions, versions, and actions sufficient to reconstruct what happened. |
| End-to-end run | Execution from loading inputs through final outputs, with mocks where explicitly allowed. |
| Deployment | Making the workflow available in its intended runtime with scheduling, credentials, and ownership. A full deployment pipeline is not required. |
| Architecture | The major components, responsibilities, and connections of a system. A formal diagram is optional here. |
| Prototype / production-grade | An implementation demonstrating the idea / a system engineered for sustained operational use. The assignment asks for a working prototype. |

## 9. Monitoring and reliability terminology

| Term | Meaning | Example for this exercise |
|---|---|---|
| Monitoring | Repeated measurement and review of system behavior and outcomes. | Watch data quality, score behavior, actions, and eventual conversions. |
| Logging | Recording events or details from execution. | Useful evidence, but logs alone do not define when to act. |
| Health check | A check that a component or workflow can operate. | Verify that a batch loads and scores successfully. |
| Data-quality assertion | A concrete requirement checked against input data. | Required columns exist; count fields are nonnegative integers. |
| Schema | Expected column names, types, and structure. | Detect a renamed or missing `employee_count` column. |
| Data contract | Agreed meanings, formats, availability, and timing of data. | Define what counts as a sales contact and its 90-day window. |
| Freshness / staleness | How current / out-of-date information is for its intended use. | Calculate snapshot age using 2026-08-01, then choose a justified policy. |
| Data / covariate drift | A change in input distributions. | Intent availability or company-size mix changes. |
| Prediction / score drift | A change in the distribution of model outputs. | An unusually large share of accounts receives high scores. |
| Concept drift | A change in the relationship between inputs and outcomes. | Trial usage stops being as predictive of conversion. |
| Performance degradation | Deterioration in predictive or business results. | Top-ranked accounts convert less often after label maturity. |
| Calibration drift | Predicted probabilities become less aligned with observed rates. | The same score band produces lower realized conversion rates. |
| Training-serving skew | A difference between how training and live features are produced. | Live sales contacts count attempts, while training counted completed conversations. |
| Silent failure | Incorrect or unhelpful output without a crash. | A vendor stops updating intent, but scoring still succeeds. |
| Alert condition / threshold | A defined rule that identifies a state needing attention. | A meaningful increase in missingness sustained across sufficient batches. |
| Noise | Random or expected variation that does not establish a real change. | One small batch has fewer conversions by chance. |
| Minimum sample size | Required evidence volume before interpreting a metric or alert. | Avoid declaring a segment broken after one negative outcome. |
| Persistence window | How long a condition must hold before an alert triggers. | Require sustained changes where an immediate response is unnecessary. |
| Seasonality | Repeating time-related changes. | Holiday periods can alter engagement independently of model quality. |
| PSI | Population Stability Index: a binned distribution-change measure, commonly written `sum((current - reference) × ln(current / reference))`. | Requires fixed bins and handling of zero proportions. It does not establish a loss of business value, and cutoffs are not universal. |
| Alert fatigue | Reduced attention caused by too many low-value alerts. | Use actionable signals with clear owners. |
| Runbook | A documented response to a known operational issue. | Inspect vendor coverage, pause affected actions if warranted, and recover. |
| Fallback | A defined alternative when the normal path is unreliable. | Route affected accounts to review or an agreed baseline worklist. |
| Feedback loop | System actions influence the future data used to evaluate or train it. | Only calling high-score accounts changes which outcomes become observable. |
| Outcome monitoring | Tracking whether the business result still improves. | Compare mature conversion outcomes under a defensible evaluation design. |

## 10. Exercise and delivery terminology

| Term | Meaning in this assignment |
|---|---|
| Take-home exercise | A candidate assignment completed outside the interview meeting. |
| Time-box / deadline | Suggested effort of about 4 hours / a hard submission cutoff 24 hours after receipt. |
| Scope / mandate / specification | Work boundaries / a broad objective / detailed requirements. The VP's request is deliberately a vague mandate. |
| Stakeholder | A person affected by the work or involved in its decisions, such as a rep or sales leader. |
| Constraint / resourcing limit | A restriction on what can be done, such as time, staff, data, or budget. |
| Starter scaffold | Initial files and directory structure supplied to begin the project. |
| Dependency / pinned dependency | An external software package / a package fixed to a specified version for reproducibility. |
| Repository / repo | A version-controlled collection of project files. |
| Git / commit / history | Version-control system / recorded change / sequence showing how work developed. |
| Push / public repository | Upload commits to a remote repository / make its contents publicly accessible. This is the requested submission mechanism. |
| Squash | Combine several commits into one. The exercise asks for real incremental history instead. |
| Markdown / `.md` | Plain-text document format supporting headings, links, lists, and code blocks. |
| `README.md` | Setup and run instructions. |
| `requirements.txt` | Python dependency list. |
| `.pkl` / pickle | Python object serialization format; `model/model.pkl` stores the supplied trained object. |
| `PROPOSAL.md` | Roughly 800–1,200 words covering impact, agent design/deployment, and monitoring. |
| `RESEARCH-LOG.md` | Contemporaneous hypotheses, findings, prompts, responses, dead ends, and corrections; its final entry gathers raw presentation material. |
| Pseudocode | A precise description of logic without requiring executable syntax. Allowed for a monitoring component. |
| Config stub | A minimal configuration example illustrating how deployment or another setup would work. |
| Test suite | A collection of automated checks. A formal suite is not required for this prototype. |
| Packaging | Preparing software for standardized distribution or installation. Not required here. |
| CI/CD | Continuous integration / continuous delivery or deployment: automated integration checks and release processes. Not required here. |
| Live run / demo | Executing the agent during the follow-up presentation. |
| Assisted coding tools | Tools used to help author or change code; the brief names Claude Code, Codex, Cursor, and Antigravity as examples. |
| Google Slides / Figma | Presentation or visual-design tools mentioned as optional ways to communicate the work. |
| Panel | The group conducting the follow-up discussion and introducing new constraints. |

## 11. This agent's implementation vocabulary

The sections above are general reference. This section documents the *specific* operational
choices this repo's agent (`agent/`) actually made — where a general term above (Tier,
Reason code, Human review, etc.) got a concrete definition, this is that definition. Numbers
here are specific to `data/accounts_to_score.csv` scored as of 2026-08-01.

| Term (as used in this repo) | What it concretely means here |
|---|---|
| **Track** | Which persona owns the account, derived directly from `account_type`: `SDR_Outbound` (Prospect/Suspect — cold outreach) or `AM_WinBack` (Former Customer — win-back). Set by `agent/tools.py::assign_track`. |
| **Tier** (Hot / Warm / Cold) | A *relative* priority bucket within the current batch, not an absolute probability cutoff. Hot = top 10% of this batch's predicted probabilities, Warm = next 30%, Cold = the rest. Percentile-based specifically because the model's raw probabilities are compressed (roughly 3.5%–27%, median ~5%) — a fixed cutoff like ">50%" would select zero accounts. Set by `agent/tools.py::assign_tiers`. This is a ranking convenience, not a claim that Hot-tier accounts have any particular absolute conversion rate in production. |
| **`needs_review`** | A safety flag meaning "the agent doesn't trust this row enough to act on it with full confidence — have a person check it first." Set when the snapshot date is unparseable, snapshot age exceeds 365 days, or a required numeric field is missing. **Not** set just because `intent_score` is missing (that's an expected ~40% vendor coverage gap the model itself imputes around). A flagged account is still scored and shown — this is "double-check," not "hide." In the current batch, 42 of 300 accounts (14%) are flagged, all for stale snapshots. |
| **Reason codes** | A deterministic, non-LLM explanation of why an account scored the way it did: the top 3 features by (model feature-importance × distance from the population median), rendered as plain-English sentences (e.g. "has been more active on the website than usual"). This is a simple heuristic, explicitly not SHAP or a causal explanation — see "Reason code" in section 8 and "Correlation / causation" in section 7. |
| **Draft outreach** | LLM-generated (or mock-generated) starting text for a rep's first outreach, produced only for the top 20 Hot-tier accounts by probability. See "Mock / stand-in" in section 8 — the default backend is a documented, deterministic mock; a real Groq call is a drop-in swap behind the same interface. |
| **Score drift (PSI)** | Population Stability Index (see section 9) between the training set's and a new batch's predicted-probability distributions. This repo uses standard thresholds: PSI < 0.10 stable, 0.10–0.20 warn, > 0.20 fail. Today's batch: PSI ≈ 0.006 (stable). |
| **Business-outcome proxy** | The calibration-by-decile check described conceptually in section 9's "Calibration drift" — precisely specified in `monitoring/checks.py::check_business_outcome_proxy` but marked `not_runnable` today since this batch has no mature 90-day outcomes yet. |
| **Lift (~4.1x)** | Computed *in-sample* on `training_data.csv`: accounts in the top predicted-probability decile convert at 26.7% vs. 6.5% overall. Per section 6 ("Base rate," "Holdout / out-of-sample evaluation"), this is not a held-out validation and should not be read as a deployment forecast — it is the *relative* signal being defended, not the absolute rate. |

## 12. Questions to clarify before operational use

1. What exact event does `converted_within_90d` represent, and where does its 90-day window start?
2. Are negative labels fully observed, especially for recent snapshots?
3. Does `snapshot_date` identify the time all features were measured, the last record update, or something else?
4. Are 90-day counts unique people, accounts, sessions, events, or attempts, and are their windows aligned?
5. What qualifies an MQL, an active trial user, and a sales contact?
6. What are the intent vendor's score scale, update cadence, and missing-value meanings?
7. How do accounts enter the training sample, and how does that sample compare with the cold-account population?
8. What are rep capacity, ownership rules, contact restrictions, conversion value, and outreach costs?

## Sources

- Local take-home exercise: `Take-Home_Exercise_—_Candidate_Copy_(1).md`, converted from the supplied PDF.
- Local setup and model contract: `README.md`.
- Directly inspected data: `data/training_data.csv` and `data/accounts_to_score.csv`; the summary above reflects the supplied static files.
- [Salesforce glossary](https://help.salesforce.com/s/articleView?id=glossary.htm&language=en_US&type=0): CRM record and object vocabulary.
- [Salesforce sales terminology guide](https://www.salesforce.com/blog/sales/sales-terms/): supplementary sales terminology.
- [IBM RFM analysis](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=marketing-rfm-analysis): standard RFM components and scoring concept.

All proposed examples, open questions, proxy suggestions, and additional concepts are explanatory additions rather than facts established about Cordilla.

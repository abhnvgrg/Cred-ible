# The scoring engine: how a score is produced, and what the tests pin

This document covers `app/agents.py`, `app/resolver.py`, and
`app/statement_parser.py` — the path from raw alternative-data signals to a
credit score. The code carries no commentary, so the reasoning lives here.
For authentication, see [authentication.md](authentication.md).

---

## The pipeline

```
statement file  ->  statement_parser  ->  BorrowerSignalInput
                                                |
                                                v
                       four agents, run concurrently
                       income | repayment | lifestyle | compliance
                                                |
                                                v
                                    resolver.resolve_scores
                                                |
                                                v
                       score 300-850, risk band, loan limit, factors
```

Each stage is deterministic. Given the same signals, the same score comes out
every time, and there is a test asserting exactly that at every level: each
agent, the orchestrator, the resolver, and the parser. For a credit decision
that is not a nicety — an applicant scored twice must not get two answers.

---

## The four agents

Three produce a 0-100 score with a confidence level and flags; the fourth
produces a compliance verdict.

| Agent | Reads | Rewards | Penalises |
|---|---|---|---|
| **Income stability** | UPI, employment, GST | regularity, history depth, work tenure, documented proof | declining volume, self-declared proof, missed GST filings |
| **Repayment behaviour** | rent, utilities, existing EMI | on-time ratios, unbroken payment history | late payments, long gaps, erratic EMI |
| **Lifestyle risk** | mobile app usage | recharge consistency, finance-app engagement | risky-app usage, erratic recharges |
| **Compliance and fraud** | declared attributes, overall profile | — | prohibited attributes, fraud-risk patterns |

All four run concurrently under `asyncio.gather` in `run_all_agents`. They do
not depend on each other's output, which is what makes that safe.

**The LLM is optional and falls back.** `run_all_agents` dispatches through
`_run_scoring_agent_with_fallback`, so when `CREDIBLE_LLM_ORCHESTRATION` is off
— or when the LLM call fails — the deterministic rule-based agent runs instead.
A test asserts the orchestrator's output matches the individual rule agents
exactly in that mode, so the fallback path is not merely present but verified
equivalent.

### Prohibited attributes

`compliance_and_fraud_agent` marks a profile non-compliant if `declared_attributes`
contains an attribute lending must not consider. This is a legal requirement,
not a heuristic, so it is tested from both sides: prohibited attributes are
caught, and neutral ones (`city`, `language`) are not — a false positive here
would deny credit for no reason.

---

## The resolver

### Weighting

`income 40% / repayment 40% / lifestyle 20%`, asserted to sum to 1.0. The
weights are returned in the response and the per-component contributions are
returned alongside, so a reader can reconstruct the arithmetic rather than
trust it. A test does exactly that reconstruction.

Lifestyle is deliberately the smallest weight: it is the softest signal and the
one most likely to encode something unfair. A test pins that income moves the
score more than lifestyle does, so a future reweighting cannot quietly invert
that priority.

### The 300-850 band

`internal_score * 5.5 + 300`, clamped. 0 maps to 300 and 100 maps to 850, and a
test sweeps every value from -50 to 200 to confirm the output never leaves the
band regardless of what upstream produces.

Risk bands: `>= 760` low, `>= 620` medium, below that high. Tested at every
boundary on both sides, because an off-by-one at 620 is the difference between
an approval and a rejection.

### Compliance penalties

Subtracted from the internal score before scaling:

| Condition | Penalty |
|---|---|
| Each compliance flag | 1.8, capped at 14.0 |
| Fraud risk medium | +8.0 |
| Fraud risk high | +18.0 |
| Not RBI compliant | +10.0 |
| **Total** | **capped at 36.0** |

The cap matters. Without it a profile with many flags could be driven to the
floor by accumulated small penalties, making the flag count rather than the
underlying risk dominate the score.

### Confidence

Blends the three agents' own confidence, then subtracts for **disagreement**
between them, for compliance penalties, and for non-compliance. The
disagreement term is the interesting one: three agents that all say 70 are more
trustworthy than three that say 100, 70, and 0 while averaging the same. A test
pins that the split profile is never more confident than the agreed one.

### Recommended loan limit

A base band from the score, adjusted by a profile multiplier built from income,
income stability, rent punctuality, and repayment stress — clamped to
`[0.75, 1.75]` so the multiplier can never dominate the score itself. A minimum
spread of ₹40,000 is enforced so the range is never degenerate.

Amounts are formatted in the Indian grouping system (`₹1,00,000`, not
`₹100,000`), tested up to a crore.

---

## The statement parser

Accepts CSV and Excel, normalises column names, and finds columns by alias, so
`Date` / `transaction_date` / `txn_date` all work. Unsupported extensions,
empty files, missing required columns, and unknown signal types are all
rejected with a clear `ValueError` rather than producing a partial result.

Derived fields are validated against the same Pydantic schemas the API uses —
there is a test that constructs `UPISignal(**derived_fields)` directly, so the
parser cannot drift from the schema it feeds.

### A real bug this found

`_longest_month_gap` computed the gap between two months as:

```python
gap = int(current - previous) - 1
```

On pandas 2.x, subtracting two `Period` objects returns a `MonthEnd` offset,
not an integer, and `int()` on it raises:

```
TypeError: int() argument must be a string, a bytes-like object or a real
number, not 'pandas._libs.tslibs.offsets.MonthEnd'
```

`requirements.txt` pins `pandas==2.3.3`, so this failed for **every rent
statement spanning two or more distinct months** — which is every real one. It
now reads the offset's `.n`, with a fallback for older pandas where the
subtraction did return an integer.

This is the clearest argument for the tests in this document: the function was
in production, on the path every rent upload takes, and nothing had ever
executed it against more than one month of data.

---

## Test coverage

| File | Cases | Covers |
|---|---|---|
| `tests/test_resolver.py` | 59 | weighting, banding, penalties, confidence, loan limits, formatting |
| `tests/test_agents.py` | 41 | scoring primitives, all four agents, orchestration, extremes |
| `tests/test_statement_parser.py` | 38 | column handling, trends, gaps, all five signal types, malformed input |
| `tests/test_auth.py` | 50 | see [authentication.md](authentication.md) |
| **Total** | **188** | |

`tests/factories.py` builds `strong_borrower()` and `weak_borrower()` profiles
with deep-merge overrides, so a test changes one field and states what it is
testing rather than restating a forty-line payload.

### What the tests assert, and why those things

Rather than pinning exact scores — which would break on any legitimate
reweighting and teach nothing — most tests pin **relationships**:

- A better profile never scores lower than a worse one.
- Raising any single component raises the score.
- Every agent prefers the strong profile to the weak one.
- Every agent stays inside 0-100 on both extremes of valid input.
- Scoring is deterministic.

These survive tuning and still catch a sign error, an inverted comparison, or a
clamp that stops clamping.

---

## Known limits

- **`/score` and `/model/predict-risk` are unauthenticated.** Anyone who can
  reach the API can score arbitrary profiles. `/model/train` is admin-gated;
  scoring is not.
- No test covers the LLM-backed agent path itself — only that the fallback to
  rules is equivalent. Exercising it needs a stubbed LLM client, which
  `app/agents.py` does not currently allow to be injected.
- The ML model in `app/ml_model.py` is covered only by its traversal and
  authorisation tests. Training and prediction accuracy are untested.
- The scoring weights and thresholds are unvalidated against any real default
  data. They are plausible, not calibrated, and the disclaimer in every
  response says so.
- Agent concurrency is tested for correctness, not for behaviour under load.

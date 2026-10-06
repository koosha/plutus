# Changelog

This file starts with 1.2.0. Earlier changes are described in the git history
and in the README's compatibility notes.

## 1.2.0 — 2026-10-05

Hooks a host needs to qualify a replacement model and to change its prompt
without a package release. Existing hosts need no code change: every new
argument is optional, new result fields are additions, and `error_type` keeps
its values. Unusable completions that 1.1.0 returned as successes are now
failures, so those outcomes take a host's error path instead of its output
checks (see Changed).

### Added

- Prices and allowed names for `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`,
  `gpt-6-luna` and `gpt-6-sol` (standard rates on the provider's global
  endpoint, checked on 2026-10-04), each accepted alone or with a dated
  snapshot suffix (`-YYYY-MM-DD`). The pricing version is now dated
  2026-10-04. These five families bill input written to the prompt cache,
  which is on by default, at 1.25x the input rate, so their input is charged
  at that cache-write rate: on the global endpoint `maximum_cost()` is a true
  ceiling and a settled cost is an upper bound of the bill. Cached-input
  rates are documented but not modelled. Regional processing (data
  residency) and FedRAMP endpoints charge 10% more for models released on or
  after 2026-03-05, which that ceiling does not cover.
- The `gpt-5.6-sol` rate (4.00 / 20.00) is promotional: on 2026-10-05 the
  provider said it is available at least through 2026-11-21 and published no
  later price. Re-check it, and bump the pricing version if it changed,
  before qualifying `gpt-5.6-sol` or keeping it in use after that date.
- `OpenAIProvider.complete()` refuses a model without a reviewed price before
  any request, raising `LLMModelNotPricedError` (a `LLMNotConfiguredError`).
- Typed provider errors, all subclasses of `LLMResponseError`, each with a
  stable `category` and a `retryable` flag: authentication, quota, rate limit
  (with `retry_after` from the response headers), provider unavailable,
  timeout, model not found, invalid request, empty, truncated, filtered and
  malformed completions. `ERROR_CATEGORIES` lists the categories.
- Orchestrator results carry `metadata.error_category`, `metadata.retryable`
  and, when stated, `metadata.retry_after_seconds` and the refused request's
  `metadata.rate_limit`. `error_type` is unchanged (`llm_error` or
  `llm_not_configured`).
- `metadata.llm.requested_model` beside `metadata.llm.model` (the model the
  provider served), and `metadata.llm.rate_limit` with the request and token
  limits, remaining amounts and reset times read from the same response.
- Host-supplied system prompts: `PlutusOrchestrator(system_prompt=...,
  brief_system_prompt=..., prompt_version=...)`. The default is the existing
  prompt, byte for byte, under version `package-default`; every result
  records `metadata.prompt_version`. A brief prompt is derived from a host
  chat prompt only when exactly one line begins with `Output contract`;
  everything from that line on is replaced by the brief card contract.
  Otherwise the host supplies `brief_system_prompt`.
- `plutus.agents.boundaries.apr_fraction(value, unit=None)` and the optional
  account field `interest_rate_unit` (`percent` or `fraction`).

### Changed

- A completion that stops at the output-token limit, has no text, or is
  filtered raises a typed error instead of returning partial or empty text.
  The error keeps the paid usage (`error.completion`, text removed) and the
  orchestrator reports it under `metadata.llm`, so the actual cost can still
  be settled.
- Consequences a host can see, although `error_type` keeps its values:
  - a brief completion (`output_contract="brief"`) that was empty, refused,
    filtered or stopped at the output-token limit used to arrive as a
    success, left to the host's own card checks; it now arrives as
    `llm_error` with `error_category` `empty_completion`,
    `content_filtered` or `truncated_completion`, so the host's
    provider-error path handles it;
  - a chat completion that stopped at the limit or was filtered used to
    arrive as a success when its text still passed the chat checks: plain
    text, returned verbatim, or a complete JSON answer. It now arrives as
    `llm_error` with `truncated_completion` or `content_filtered`;
  - a chat completion that was empty or refused, or was cut off or
    filtered inside its JSON object, was already `llm_error` and already
    reported its usage under `metadata.llm`; only its `error_category` is
    new;
  - a response without choices was the only unusable completion that
    carried no usage, so the host kept its reserved maximum; it now reports
    its usage under `metadata.llm` (`error_category` `empty_completion`)
    and settles at the reported cost. Every other unusable completion
    above reported its usage before and still does;
  - a refused request's rate-limit headers are at `metadata.rate_limit`;
    `metadata.llm` appears only when a completion was received.
- The provider reads each completion through the SDK's raw-response access to
  capture rate-limit headers; no extra request is made.
- The recommendation and risk specialists read interest rates on one scale.
  The recommendation specialist treated rates as percentages and missed
  fractional rates; the risk specialist treated them as fractions and flagged
  an 18% rate as high-interest. Thresholds are unchanged (above 15% and 20%
  APR). A negative or unrecognised-unit rate now makes debt risk unknown.
- The `langgraph` extra requires LangGraph `>=1.2.4,<1.3` and langgraph-sdk
  `>=0.4.4,<0.5` (it required `>=1.0.10,<1.1` and `>=0.3.15,<0.4`), because
  the SDK fix in Security needs LangGraph 1.2. Minimal mode is unchanged.

### Removed

- The risk specialist's INFO log line with the user's overall risk score.
- Python 3.9 support. Advisories published on 2026-10-01 (PYSEC-2026-4024,
  PYSEC-2026-4025) affect every anyio release that supports Python 3.9, so
  that installation can no longer be audited clean; CPython 3.9 itself has
  been end-of-life since October 2025. Python 3.10 or newer is required. See
  `docs/graph-dependencies.md`.

### CI

- The Python 3.9 job was the only one that ran SDK 2.x, the major Wealthify
  deploys. A new `host-sdk` job installs Wealthify's SDK pins (2.48.0) into
  the locked Python 3.12 minimal environment and runs the whole suite, so the
  provider's raw-response access, exception mapping and header capture are
  tested on both SDK majors.

### Security

- urllib3 2.8.0 in the lock (PYSEC-2026-4175, PYSEC-2026-4176,
  PYSEC-2026-4177; graph mode only).
- langgraph-sdk 0.4.5 and LangGraph 1.2.12 in the lock (GHSA-fvww-7h3r-vfhp,
  CVE-2026-104873, published 2026-10-05; graph mode only). The advisory
  concerns the SDK's custom authorization handlers, which Plutus does not
  use; see `docs/graph-dependencies.md`.

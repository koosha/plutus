# Plutus

Plutus provides financial analysis and educational response synthesis for Wealthify. The host supplies authorized financial context and owns authentication, consent, persistence, and spending controls. Domain specialists organize findings before an injected asynchronous provider produces a response.

## Install

Plutus supports Python 3.10 or newer, in minimal mode and in the optional graph mode. Python 3.9 support ended in 1.2.0 (see the [changelog](CHANGELOG.md)). Use the exact reviewed repository revision or a wheel built from that revision:

```bash
git clone https://github.com/koosha/plutus.git
cd plutus
python -m pip install .
```

For development, install uv and use the checked-in lock:

```bash
uv sync --locked --extra dev
uv run --no-sync pytest -q
uv build --wheel
```

The optional graph installation is tested separately with `uv sync --locked --extra dev --extra langgraph`. Both supported installations must execute the same selected analyses. A missing optional dependency must not change financial conclusions. See [graph dependency security and compatibility](docs/graph-dependencies.md) for the patched minimum versions and evaluation boundary.

## Use

```python
from plutus import PlutusOrchestrator

orchestrator = PlutusOrchestrator(provider=your_provider)
result = await orchestrator.process_message(
    "Help me understand my cash flow",
    user_id="example-user",
    user_context=authorized_context,
)
```

`provider` implements `plutus.llm.LLMProvider`. Production may configure `OPENAI_API_KEY` and `PLUTUS_MODEL`; no credentials are needed to import the package or run the tests. A missing provider produces a typed unavailable result. This library does not start a web server or load sample financial data at runtime.

The host owns configuration loading. Plutus reads explicit process environment
variables and constructor settings; importing it never discovers or loads a
repository-local `.env` file. Applications that previously relied on that implicit
behavior must load their chosen configuration before importing or constructing
Plutus. The package no longer depends on `python-dotenv`.

Run the complete offline example after installation:

```bash
python examples/offline_chat.py
```

CI also runs this example in an isolated wheel environment outside the source checkout, ensuring that source-path injection cannot hide packaging omissions. The public `plutus.PlutusOrchestrator` and historical `plutus.agents.orchestrator.PlutusOrchestrator` imports remain supported.

## Models and pricing

`OpenAIProvider` sends one Chat Completions request per answer through the model provider's official async SDK. It dispatches only models with a reviewed price: a listed family name, alone or with a dated snapshot suffix (`-YYYY-MM-DD`, for example `gpt-5.6-terra-2026-10-01`). For any other name `maximum_cost()` returns `None`, so a host can refuse before reserving spend, and `complete()` raises `LLMModelNotPricedError` before a request is sent.

Standard text prices, USD per million tokens, checked on 2026-10-04 (`plutus.llm.pricing.PRICING_VERSION` names this table):

| Model | Input | Cache writes | Output | Cached input (not modelled) |
| --- | --- | --- | --- | --- |
| `gpt-5` | 1.25 | none | 10.00 | 0.125 |
| `gpt-5-mini` | 0.25 | none | 2.00 | 0.025 |
| `gpt-5-nano` | 0.05 | none | 0.40 | 0.005 |
| `gpt-5.6-luna` | 0.20 | 0.25 | 1.20 | 0.02 |
| `gpt-5.6-terra` | 2.00 | 2.50 | 12.00 | 0.20 |
| `gpt-5.6-sol` | 4.00 | 5.00 | 20.00 | 0.40 |
| `gpt-6-luna` | 0.10 | 0.125 | 0.50 | 0.01 |
| `gpt-6-sol` | 2.00 | 2.50 | 10.00 | 0.20 |

Prompt caching is on by default. The 5.6 and 6 families bill input written to the cache at 1.25x the uncached input rate, and caching writes a prompt up to its latest message, so most input of a large prompt is billed at that rate; the gpt-5 family has no cache-write charge. Plutus charges every input token at the highest rate the provider can bill for it: the cache-write rate where the family has one, otherwise the uncached rate. `maximum_cost()` is therefore a true ceiling for the host's reservation, and a settled cost is an upper bound of the bill. The bill is lower when input is served from the cache, or on the 5.6 and 6 families is not written to it; those discounts are not modelled. The 5.6 and 6 families cost 2x input and 1.5x output above 272K input tokens; Plutus bounds each request far below that. The provider's model pages, checked on 2026-10-05, list Chat Completions support for all five newer families and publish no dated snapshots for them yet. Whether each model accepts the request parameters (`max_completion_tokens`, temperature omitted by default) and produces usable output within the output budget is not established by these tests; that needs a live qualification run.

## Provider errors

Every provider failure is a subclass of `LLMResponseError`, so existing `except LLMResponseError` and `except LLMError` clauses still catch it. Each exposes a stable `category` and a `retryable` flag:

| Category | Error class | Retryable | Meaning |
| --- | --- | --- | --- |
| `authentication_failed` | `LLMAuthenticationError` | no | Invalid or revoked key, or the key may not use the model (401, 403) |
| `quota_exhausted` | `LLMQuotaExhaustedError` | no | The account's quota or billing allows no more requests |
| `rate_limited` | `LLMRateLimitError` | yes | Request or token rate limit; `retry_after` from `retry-after-ms` or `retry-after` |
| `provider_unavailable` | `LLMProviderUnavailableError` | yes | 5xx, overload, conflict, or no connection |
| `timeout` | `LLMTimeoutError` | yes | No complete response within the configured time |
| `model_not_found` | `LLMModelNotFoundError` | no | The model does not exist or is not served on this endpoint (404) |
| `invalid_request` | `LLMInvalidRequestError` | no | The provider rejected the request itself, for example a parameter (400, 413, 422) |
| `empty_completion` | `LLMEmptyCompletionError` | no | No text, or no choices |
| `truncated_completion` | `LLMTruncatedCompletionError` | no | Output stopped at the output-token limit (`finish_reason` `length`) |
| `content_filtered` | `LLMContentFilteredError` | no | Output filtered, or the model refused without an answer |
| `malformed_completion` | `LLMMalformedCompletionError` | no | Text that does not satisfy the requested output contract |
| `provider_error` | `LLMResponseError` | no | Any other failure |

`LLMNotConfiguredError` (`not_configured`) and its subclass `LLMModelNotPricedError` (`model_not_priced`) mean no request could be made. Retryable means only that an identical request may succeed later without operator action; output failures are not retryable because a repeat is likely to fail the same way and is charged again. A truncated, empty or filtered completion is never returned as a partial success. Its error carries the paid usage in `error.completion` (text removed) so the host can settle the actual cost. Error messages are fixed text; provider error bodies are not copied into them.

## Host-supplied system prompt

The host may supply the synthesis system prompt and a version id for it, so a prompt it has evaluated can change without a package release:

```python
orchestrator = PlutusOrchestrator(
    provider=your_provider,
    system_prompt=host_chat_prompt,
    brief_system_prompt=host_brief_prompt,  # optional
    prompt_version="host-chat-2026-10-05",
)
```

With no arguments the package default `ADVISOR_SYSTEM_PROMPT` is used unchanged, under version `package-default`. Without `brief_system_prompt`, the brief prompt is the chat prompt up to its `Output contract` section followed by the package's brief card contract. A host chat prompt without an `Output contract` section needs its own `brief_system_prompt`; otherwise the brief would carry the chat output contract beside the card contract. A host prompt requires its own version id (1-64 letters, digits, `.`, `_`, `:` or `-`, never `package-default`), and a version id other than `package-default` requires a host prompt, so answers cannot be attributed to the wrong prompt. Each prompt sent is at most 8,192 UTF-8 bytes, which together with the 24,000-byte user prompt keeps a request's input below 32,768 tokens. Invalid prompt settings raise `ValueError` when the orchestrator is constructed. Prompt text never appears in results, logs or error messages.

## Result metadata

Every result from `process_message` records `metadata["prompt_version"]`. When a completion was received, including a charged completion that was then rejected, `metadata["llm"]` contains:

- `model`: the model the provider reports having served, and `requested_model`: the name that was asked for (`None` when the provider does not say);
- `input_tokens`, `output_tokens`, `api_cost`, `cost_status` and `pricing_version`;
- `rate_limit`: the provider's `limit`, `remaining` and `reset` values for requests and tokens (`limit_requests`, `remaining_requests`, `reset_requests_seconds`, `limit_tokens`, `remaining_tokens`, `reset_tokens_seconds`), read from the same response, or `None` when not reported. A header that is absent or does not parse is `None`, never zero.

On failure, `error_type` keeps its existing values (`llm_error`, `llm_not_configured`, `orchestration_error`). Provider-layer failures add `metadata["error_category"]` and `metadata["retryable"]`, plus `retry_after_seconds` and the refused request's `rate_limit` when the provider stated them.

## Financial inputs

Account `interest_rate` values may be percentages (24.99) or fractions (0.2499). A context may state the scale with `interest_rate_unit` (`percent` or `fraction`); without it, a value greater than 1 is read as a percentage. Missing, negative or unrecognised rates are unknown and are not treated as zero. Every specialist reads rates through `plutus.agents.boundaries.apr_fraction`.

## Verification boundaries

Unit and integration tests use injected providers and synthetic data. They verify contracts and failure handling without paid model calls. They do not establish live-model answer quality, production availability, or suitability of financial advice. Host integration and opt-in provider evaluations must record their actual modes and model versions.

Conversation history belongs to the host. The historical standalone SQLite memory service is not part of the supported runtime. Project changes use `plutus/` branches and the repository owner's commit identity.


## Compatibility and storage

The public orchestrator imports remain supported. The unused internal SQLite
`services.memory_service` and unused prompt/validation mixins were retired in
1.1.0. Their default construction was already broken and they had no active
package consumer. Integrations must persist conversations in their host and
pass bounded `conversation_history` with the current authorization provenance.
No database file is created by importing or constructing Plutus.

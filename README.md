# Plutus

Plutus provides financial analysis and educational response synthesis for Wealthify. The host supplies authorized financial context and owns authentication, consent, persistence, and spending controls. Domain specialists organize findings before an injected asynchronous provider produces a response.

## Install

Minimal mode supports Python 3.9 or newer. Optional graph mode requires Python 3.10 or newer. Use the exact reviewed repository revision or a wheel built from that revision:

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

On Python 3.10+, the optional graph installation is tested separately with `uv sync --locked --extra dev --extra langgraph`. Python markers omit graph dependencies on 3.9; select a supported newer interpreter to use graph mode. Both supported installations must execute the same selected analyses. A missing optional dependency must not change financial conclusions. See [graph dependency security and compatibility](docs/graph-dependencies.md) for the patched minimum versions and evaluation boundary.

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

Run the complete offline example after installation:

```bash
python examples/offline_chat.py
```

CI also runs this example in an isolated wheel environment outside the source checkout, ensuring that source-path injection cannot hide packaging omissions. The public `plutus.PlutusOrchestrator` and historical `plutus.agents.orchestrator.PlutusOrchestrator` imports remain supported.

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

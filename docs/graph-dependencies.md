# Optional graph dependencies

Minimal Plutus supports Python 3.9+. Graph mode supports Python 3.10+ because the
patched graph releases require that interpreter minimum. The optional dependency
markers omit graph packages on 3.9. CI covers 3.9 minimal, 3.10 graph, and both
3.12 modes. Graph CI explicitly asserts that graph support imported successfully
before running the contract suite, so a broken import cannot pass through skips.

## Security disposition — 2026-09-10

The previous lock selected LangGraph 0.6.6 and older graph dependencies. Upstream
reports unsafe object reconstruction when loading attacker-modified persistent
checkpoints: **GHSA-g48c-2wqr-h844**, Moderate, CVSS 6.8, patched in LangGraph
1.0.10. Plutus compiles its graph without a persistent checkpointer and does not
load checkpoints, so that prerequisite is absent in the supported application
path. The optional dependency is nevertheless upgraded rather than treating the
unused path as justification to retain an affected supported version.
[Upstream advisory](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-g48c-2wqr-h844).

| Component | Minimum version | Reason |
| --- | --- | --- |
| LangGraph | 1.0.10, below 1.1 | Patched checkpoint-loading hardening; Python 3.10+ |
| langchain-core | 1.3.3, below 2 | Includes template and serialization fixes, including GHSA-pjwx-r37v-7724 |
| langgraph-sdk | 0.3.15, below 0.4 | Includes identifier/path handling fix for CVE-2026-48776 |
| langgraph-checkpoint | 4.1.1, below 5 | Includes checkpoint deserialization fix for CVE-2026-48775 |

The exact reviewed resolution belongs in `uv.lock`. Package metadata establishes
safe lower bounds; it does not replace the lock. Version requirements and
published advisories were checked against the release metadata for
[LangGraph 1.0.10](https://pypi.org/pypi/langgraph/1.0.10/json),
[langchain-core 1.3.3](https://pypi.org/pypi/langchain-core/1.3.3/json),
[SDK 0.3.15](https://pypi.org/pypi/langgraph-sdk/0.3.15/json), and
[checkpoint 4.1.1](https://pypi.org/pypi/langgraph-checkpoint/4.1.1/json).
Those release records listed no vulnerabilities when reviewed; that is a dated
observation, not a permanent security guarantee.

## Host compatibility and validation

Wealthify's default backend/image continues to use minimal mode. Its separate
graph evaluation lane takes graph additions from the Plutus lock and preserves
all pinned backend packages. For example, langchain-core 1.3.3 allows the host's
Pydantic 2.11.7, typing-extensions 4.14.1, and packaging 24.2; graph support does
not justify downgrading patched HTTP, certificate or request dependencies.
The lane runs `pip check`, audits the combined requirements, and executes the
real host evaluations plus explicit minimal/graph parity.

The metadata update requires a newly resolved lock and green supported-mode CI
before publication is considered complete. Local source tests can confirm goal
routing and error behavior, but cannot substitute for the Python 3.10/3.12 graph
and installed-wheel runs. No paid provider call or persistent checkpointer is
used in any of these checks.

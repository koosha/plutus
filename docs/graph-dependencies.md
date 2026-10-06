# Optional graph dependencies

Plutus supports Python 3.10+ in both minimal and graph mode. Graph mode has
required 3.10 since the patched graph releases set that interpreter minimum;
minimal mode followed in 1.2.0 (see the 2026-10-05 disposition below). CI covers
both modes on 3.10 and on 3.12, and minimal mode on 3.12 with the model
provider's SDK release Wealthify pins (see "SDK coverage" below). Graph CI
explicitly asserts that graph support imported successfully before running the
contract suite, so a broken import cannot pass through skips.

## Security disposition — 2026-10-05

Advisories published on 2026-10-01 made the locked runtime audit fail:

| Package | Locked | Advisories | Fixed in | Disposition |
| --- | --- | --- | --- | --- |
| urllib3 (graph mode) | 2.7.0 | PYSEC-2026-4175, PYSEC-2026-4176, PYSEC-2026-4177 | 2.8.0 | Lock upgraded to 2.8.0, the version Wealthify already pins |
| anyio (Python 3.9 only) | 4.12.1 | PYSEC-2026-4024, PYSEC-2026-4025 | 4.14.2 | No fixed release supports Python 3.9; Python 3.9 support removed |

On Python 3.10+ the lock already resolved anyio 4.15.1, which includes the fix.
Plutus never runs anyio process pools (PYSEC-2026-4024) and connects only to the
provider's ASCII host name (PYSEC-2026-4025), so neither advisory is reachable
through Plutus. As with the 2026-09-10 graph upgrade, that is not treated as a
reason to keep an affected supported installation: anyio 4.14.2 requires Python
3.10, CPython 3.9 has been end-of-life since October 2025, and Wealthify runs
Python 3.12. Requiring Python 3.10 removes the 3.9 resolution from the lock;
every Python 3.10+ version is otherwise unchanged. The 3.9 minimal CI job is
replaced by a 3.10 minimal job.

### SDK coverage

The 3.9 resolution was also the only one that selected SDK 2.x (2.48.0); every
3.10+ resolution selects SDK 3.11.0. Removing it would have left no CI job
running the suite on SDK 2.x, which is what Wealthify deploys
(`openai==2.48.0` in `python-backend/requirements.txt`), while the 1.2.0
provider code depends on the SDK more than before: raw-response access,
mapping SDK exceptions to typed errors, and reading rate-limit headers. The
`host-sdk` CI job therefore installs Wealthify's pins for the SDK and the two
packages it adds over the lock (`openai==2.48.0`, `distro==1.9.0`,
`tqdm==4.70.0`) into the locked Python 3.12 minimal environment, asserts the
installed SDK version, and runs the whole offline suite. The suite drives the
real SDK client over an in-memory transport on either major
(`tests/provider_transport.py`), so the SDK's own status mapping and parsing
are exercised.

The boundary of that evidence: every other dependency in that job is the locked
version, not Wealthify's pin; no SDK 2.x release other than 2.48.0 is tested,
although `openai>=2.0.0` allows them; and no job makes a live provider request.
When Wealthify changes its SDK pin, update the `host-sdk` matrix with it.
[anyio advisory GHSA-82r6-8w77-94w6](https://github.com/advisories/GHSA-82r6-8w77-94w6),
[anyio advisory GHSA-5p39-cfhj-2xmp](https://github.com/advisories/GHSA-5p39-cfhj-2xmp).

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

The Python 3.9 minimal audit also exposed `python-dotenv` 1.2.1
(`PYSEC-2026-2270`). Its only Plutus use was implicit import-time `.env` loading.
That unnecessary file discovery and dependency were removed; explicit process
environment settings remain supported. The host now owns all configuration-file
loading. A fresh-import regression rejects any dotenv import or `.env` access
and verifies that explicit model, timeout and retry settings still apply.

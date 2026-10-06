# Optional graph dependencies

Plutus supports Python 3.10+ in both minimal and graph mode. Graph mode has
required 3.10 since the patched graph releases set that interpreter minimum;
minimal mode followed in 1.2.0 (see the 2026-10-05 disposition below). CI covers
both modes on 3.10 and on 3.12, and minimal mode on 3.12 with the model
provider's SDK release Wealthify pins (see "SDK coverage" below). Graph CI
explicitly asserts that graph support imported successfully before running the
contract suite, so a broken import cannot pass through skips.

## Current graph bounds

| Component | Allowed | Locked | Reason |
| --- | --- | --- | --- |
| LangGraph | 1.2.4, below 1.3 | 1.2.12 | First release that is not yanked and accepts the patched SDK below; keeps the checkpoint-loading hardening of 1.0.10 |
| langgraph-sdk | 0.4.4, below 0.5 | 0.4.5 | Fix for GHSA-fvww-7h3r-vfhp (2026-10-05); includes the fix for CVE-2026-48776 |
| langchain-core | 1.3.3, below 2 | 1.6.2 | Template and serialization fixes, including GHSA-pjwx-r37v-7724 |
| langgraph-checkpoint | 4.1.1, below 5 | 4.2.0 | Checkpoint deserialization fix for CVE-2026-48775 |

The dated dispositions below record why each bound was set or moved.

## Security disposition — 2026-10-05

Advisories published on 2026-10-01 and 2026-10-05 made the locked runtime audit
fail:

| Package | Locked | Advisories | Fixed in | Disposition |
| --- | --- | --- | --- | --- |
| urllib3 (graph mode) | 2.7.0 | PYSEC-2026-4175, PYSEC-2026-4176, PYSEC-2026-4177 | 2.8.0 | Lock upgraded to 2.8.0, the version Wealthify already pins |
| anyio (Python 3.9 only) | 4.12.1 | PYSEC-2026-4024, PYSEC-2026-4025 | 4.14.2 | No fixed release supports Python 3.9; Python 3.9 support removed |
| langgraph-sdk (graph mode) | 0.3.15 | GHSA-fvww-7h3r-vfhp (CVE-2026-104873), published 2026-10-05 | 0.4.4 | Graph extra moved to LangGraph 1.2, the first line that accepts SDK 0.4; lock upgraded to SDK 0.4.5 (see "LangGraph SDK" below) |

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

### LangGraph SDK

GHSA-fvww-7h3r-vfhp (High) concerns the SDK's custom authorization handlers: a
handler registered with `actions=` on a resource decorator, such as
`@auth.on.threads(actions=["create"])`, ran for every action on that resource,
so a LangGraph server application could skip the checks in its broader
handlers. Plutus registers no authorization handlers and runs no LangGraph
server. LangGraph 1.2 does load the SDK when its graph module is imported
(`langgraph.runtime` takes the `BaseUser` type from it), but the affected
registration code runs only when an application builds an `Auth` object. The
advisory is therefore not reachable through Plutus; as with the earlier
dispositions, that is not a reason to keep an affected installation.

Every LangGraph release before 1.2.3 requires `langgraph-sdk<0.4`, and 1.2.3
was yanked, so the fix needs LangGraph 1.2.4 or newer. The graph extra now
allows LangGraph 1.2.4 up to 1.3 and langgraph-sdk 0.4.4 up to 0.5 (it allowed
1.0.10 up to 1.1 and 0.3.15 up to 0.4). The lock moves only what that
requires: LangGraph 1.0.10 to 1.2.12, langgraph-sdk 0.3.15 to 0.4.5,
langgraph-prebuilt 1.0.13 to 1.1.0 (LangGraph 1.2 requires it), and websockets
to 16.1.1 on every Python version (SDK 0.4 requires websockets below 17; Python
3.11 and newer had resolved 17.1). Every other locked version is unchanged, and
minimal mode is not affected.

The lock selects LangGraph 1.2.12 and SDK 0.4.5, released together on
2026-09-21, rather than LangGraph 1.2.13. That release was published on
2026-10-05, hours before this lock; its changes concern checkpoint replay and
`update_state`, which a graph compiled without a checkpointer never reaches; and
two earlier releases on this line, 1.1.7 and 1.2.3, were yanked for regressions
found after publication. A later lock can take a newer release within the
bounds once it has been available for some time.

Checked for this change: the offline suite in graph mode on Python 3.10 and
3.12 with graph support asserted, the installed-wheel example in all four
modes, and a clean exact runtime audit for minimal and graph mode on both
versions. Wealthify pins websockets 15.0.1, inside the SDK's range; its graph
lane (the host's pins plus the locked graph additions) passes `pip check` and
the combined audit, and its host evaluations and graph parity pass in graph
mode. [SDK advisory GHSA-fvww-7h3r-vfhp](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-fvww-7h3r-vfhp).

## Security disposition — 2026-09-10

The previous lock selected LangGraph 0.6.6 and older graph dependencies. Upstream
reports unsafe object reconstruction when loading attacker-modified persistent
checkpoints: **GHSA-g48c-2wqr-h844**, Moderate, CVSS 6.8, patched in LangGraph
1.0.10. Plutus compiles its graph without a persistent checkpointer and does not
load checkpoints, so that prerequisite is absent in the supported application
path. The optional dependency is nevertheless upgraded rather than treating the
unused path as justification to retain an affected supported version.
[Upstream advisory](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-g48c-2wqr-h844).

These were the bounds set on 2026-09-10. LangGraph and its SDK moved on
2026-10-05; "Current graph bounds" above lists the bounds in force.

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

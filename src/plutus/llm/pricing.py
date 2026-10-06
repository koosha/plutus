"""Versioned standard text prices and the model names they cover.

A model is priced only when its name is a listed family, alone or followed by
a dated snapshot suffix (-YYYY-MM-DD). Anything else has explicitly unknown
cost, and a provider must not dispatch paid work for it.

Prices are the model provider's published standard-tier rates on its global
endpoint, checked on 2026-10-04, in USD per million tokens (input / output):

    gpt-5          1.25 / 10.00     gpt-5.6-luna   0.20 /  1.20
    gpt-5-mini     0.25 /  2.00     gpt-5.6-terra  2.00 / 12.00
    gpt-5-nano     0.05 /  0.40     gpt-5.6-sol    4.00 / 20.00  promotional
                                    gpt-6-luna     0.10 /  0.50
                                    gpt-6-sol      2.00 / 10.00

The gpt-5.6-sol rate is a promotional price. On 2026-10-05 the provider said
it is available at least through 2026-11-21 and published no price for after
that. A higher later price would make the reservation and the settled cost of
a gpt-5.6-sol request understate spend, so re-check the rate, and bump
PRICING_VERSION if it changed, before qualifying gpt-5.6-sol or keeping it in
use after 2026-11-21.

The 5.6 and 6 families also bill input written to the prompt cache at 1.25x
the uncached input rate (cache writes: gpt-5.6-luna 0.25, gpt-5.6-terra 2.50,
gpt-5.6-sol 5.00, gpt-6-luna 0.125, gpt-6-sol 2.50). Prompt caching is on by
default and writes the prompt up to its latest message, so on these families
most input of a large prompt is billed at that rate. The gpt-5 family has no
cache-write charge.

Each input token is charged here at the highest rate the provider can bill
for it: the cache-write rate where the family has one, otherwise the uncached
rate. On the global endpoint `maximum_cost()` is therefore a true ceiling for
a request Plutus composes, and a settled cost is an upper bound of the bill.
Three published rules are deliberately not modelled:

- Cached input is billed below the input rate (gpt-5-mini 0.025,
  gpt-5.6-luna 0.02, gpt-6-luna 0.01, gpt-5.6-terra 0.20, gpt-5.6-sol 0.40,
  gpt-6-sol 0.20). This lowers the bill. Settling from the provider's cached
  and written token counts would be cheaper but depends on how those counts
  overlap, so it is left out rather than risk under-stating spend.
- Prompts above 272K input tokens on the 5.6 and 6 families cost 2x input and
  1.5x output for the whole request. This surcharge raises the bill, but it
  cannot apply to a request Plutus composes: its user prompt is at most
  MAX_PROMPT_BYTES and its system prompt at most MAX_SYSTEM_PROMPT_BYTES,
  about 32K tokens together, far below that threshold.
- Regional processing (data residency) and FedRAMP endpoints charge 10% more
  for models released on or after 2026-03-05. This surcharge also raises the
  bill and is not covered: the provider class builds its SDK client without a
  base URL, so the SDK's `OPENAI_BASE_URL` environment variable chooses the
  endpoint, and on such an endpoint the bill can exceed `maximum_cost()` and
  a settled cost by up to 10%.
"""

import re
from typing import Any, Dict, Optional, Tuple

PRICING_VERSION = "openai-standard-2026-10-04"

# USD per single token (input, output), keyed by model family. The 1.1.0
# entries keep their exact literals so existing settlements are unchanged.
MODEL_COST_RATES: Dict[str, Tuple[float, float]] = {
    "gpt-5-nano": (0.05e-6, 0.40e-6),
    "gpt-5-mini": (0.25e-6, 2.00e-6),
    "gpt-5": (1.25e-6, 10.00e-6),
    "gpt-5.6-luna": (0.20e-6, 1.20e-6),
    "gpt-5.6-terra": (2.00e-6, 12.00e-6),
    "gpt-5.6-sol": (4.00e-6, 20.00e-6),
    "gpt-6-luna": (0.10e-6, 0.50e-6),
    "gpt-6-sol": (2.00e-6, 10.00e-6),
}

# USD per single input token written to the prompt cache, for the families
# that charge for cache writes (published as 1.25x the uncached input rate).
CACHE_WRITE_RATES: Dict[str, float] = {
    "gpt-5.6-luna": 0.25e-6,
    "gpt-5.6-terra": 2.50e-6,
    "gpt-5.6-sol": 5.00e-6,
    "gpt-6-luna": 0.125e-6,
    "gpt-6-sol": 2.50e-6,
}

_SNAPSHOT_SUFFIX = r"(?:-[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01]))?"
_PRICED_NAME = re.compile(
    "(" + "|".join(re.escape(family) for family in MODEL_COST_RATES) + ")" + _SNAPSHOT_SUFFIX
)


def model_family(model: Any) -> Optional[str]:
    """The priced family a model name belongs to, or None when unpriced."""
    if not isinstance(model, str):
        return None
    match = _PRICED_NAME.fullmatch(model)
    return match.group(1) if match else None


def is_priced(model: Any) -> bool:
    return model_family(model) is not None


def highest_input_rate(family: str) -> float:
    """The most the provider can bill for one input token of a priced family."""
    input_rate, _ = MODEL_COST_RATES[family]
    return max(input_rate, CACHE_WRITE_RATES.get(family, input_rate))


def cost_for(model: Any, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Versioned text pricing that never under-states a global-endpoint bill.

    Every input token is charged at `highest_input_rate`. Unrecognized models
    have explicitly unknown cost. The module docstring lists the published
    rules this leaves out, and the gpt-5.6-sol rate that is promotional.
    """
    family = model_family(model)
    if family is None:
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in (input_tokens, output_tokens)):
        return None
    _, output_rate = MODEL_COST_RATES[family]
    return input_tokens * highest_input_rate(family) + output_tokens * output_rate

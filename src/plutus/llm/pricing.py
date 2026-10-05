"""Versioned standard text prices and the model names they cover.

A model is priced only when its name is a listed family, alone or followed by
a dated snapshot suffix (-YYYY-MM-DD). Anything else has explicitly unknown
cost, and a provider must not dispatch paid work for it.

Prices are the model provider's published standard-tier rates, checked on
2026-10-04, in USD per million tokens (input / output):

    gpt-5          1.25 / 10.00     gpt-5.6-luna   0.20 /  1.20
    gpt-5-mini     0.25 /  2.00     gpt-5.6-terra  2.00 / 12.00
    gpt-5-nano     0.05 /  0.40     gpt-5.6-sol    4.00 / 20.00
                                    gpt-6-luna     0.10 /  0.50
                                    gpt-6-sol      2.00 / 10.00

Two published rules are deliberately not modelled:

- Cached input is billed below the input rate (gpt-5-mini 0.025,
  gpt-5.6-luna 0.02, gpt-6-luna 0.01, gpt-5.6-terra 0.20, gpt-5.6-sol 0.40,
  gpt-6-sol 0.20). Every input token is charged here at the uncached rate, so
  settled costs are an upper bound when the provider serves cached input.
- Prompts above 272K input tokens on the 5.6 and 6 families cost 2x input and
  1.5x output. Plutus bounds a request's input far below that threshold.
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


def cost_for(model: Any, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Versioned text pricing; unrecognized models have explicitly unknown cost."""
    family = model_family(model)
    if family is None:
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in (input_tokens, output_tokens)):
        return None
    input_rate, output_rate = MODEL_COST_RATES[family]
    return input_tokens * input_rate + output_tokens * output_rate

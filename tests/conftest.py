"""Shared test setup for the Plutus repo.

Makes `src/` importable without an editable install and provides a fake
LLM provider so no test ever touches the network.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Tests must behave identically with or without a developer's real key.
os.environ.pop("OPENAI_API_KEY", None)

from plutus.llm import LLMCompletion, LLMProvider, LLMResponseError  # noqa: E402


class FakeProvider(LLMProvider):
    """Scripted in-memory provider — records calls, returns canned output."""

    def __init__(
        self,
        payload: Optional[Dict[str, Any]] = None,
        raw_text: Optional[str] = None,
        error: Optional[Exception] = None,
        cost: float = 0.000125,
    ):
        self.calls: List[Dict[str, Any]] = []
        self._payload = payload
        self._raw_text = raw_text
        self._error = error
        self._cost = cost

    async def complete(
        self,
        messages,
        *,
        system=None,
        max_output_tokens=None,
        temperature=None,
    ) -> LLMCompletion:
        self.calls.append(
            {
                "messages": messages,
                "system": system,
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
            }
        )
        if self._error is not None:
            raise self._error
        if self._raw_text is not None:
            text = self._raw_text
        else:
            text = json.dumps(
                self._payload
                or {
                    "response": "A grounded educational answer.",
                    "insights": ["insight-1"],
                    "recommendations": ["recommendation-1"],
                    "confidence": 0.8,
                }
            )
        return LLMCompletion(
            text=text,
            model="fake-model",
            input_tokens=120,
            output_tokens=60,
            cost=self._cost,
        )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def failing_provider() -> FakeProvider:
    return FakeProvider(error=LLMResponseError("upstream 500"))

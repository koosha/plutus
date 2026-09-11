"""Installed-package smoke example; no credentials, sample files, or network."""
import asyncio
import json
from importlib.metadata import version

import plutus
from plutus import PlutusOrchestrator
from plutus.llm import LLMCompletion, LLMProvider


class ExampleProvider(LLMProvider):
    async def complete(self, messages, *, system=None, max_output_tokens=None, temperature=None):
        return LLMCompletion(
            text=json.dumps({"response": "Review your available information before setting a goal.",
                             "insights": [], "recommendations": [], "confidence": 0.5}),
            model="example", input_tokens=10, output_tokens=10, cost=0.0,
        )


async def main():
    result = await PlutusOrchestrator(provider=ExampleProvider()).process_message(
        "Help me organize my financial goals", "example-user",
        user_context={"user_id": "example-user", "accounts": [], "goals": []},
    )
    assert result["success"] is True, result
    assert result["response"] == "Review your available information before setting a goal."
    assert version("plutus") == plutus.__version__
    print("Plutus", version("plutus"), "installed-package example passed")


if __name__ == "__main__":
    asyncio.run(main())

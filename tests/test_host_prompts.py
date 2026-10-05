"""The host may supply the synthesis system prompt and its version id.

The reference digests below were computed from the prompts as they stood at
a01afda, before prompts became injectable. They pin the package default
byte for byte, independently of the code that now assembles it.
"""

import hashlib
import json

import pytest
from conftest import FakeProvider

from plutus import PlutusOrchestrator
from plutus.agents.advanced_orchestrator import ADVISOR_SYSTEM_PROMPT
from plutus.agents.system_prompts import (
    MAX_SYSTEM_PROMPT_BYTES,
    PACKAGE_DEFAULT_PROMPT_VERSION,
    resolve_prompts,
)

CHAT_SHA256 = "377529e63cb9062aede38f17cac57813498916ca0c41b1f3d37a383612d5d5cb"
BRIEF_SHA256 = "c77a630784aa5eb21f0fcc0c7e46d758292f49794e613d56fefc122b882c3a06"
BRIEF_CONTRACT = ("Output contract: return only a JSON array of brief cards with string fields "
                  "tone, title, body and action. Return [] if nothing is notable.")
HOST_PROMPT = "You are the host's evaluated advisor.\nOutput contract — reply in JSON."


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def ask(orchestrator, provider_calls_from, output_contract="chat"):
    result = await orchestrator.process_message(
        "How am I doing?", "person", user_context={}, output_contract=output_contract)
    return result, provider_calls_from.calls[-1]["system"]


class TestPackageDefault:
    def test_the_default_prompt_is_unchanged_byte_for_byte(self):
        assert sha256(ADVISOR_SYSTEM_PROMPT) == CHAT_SHA256
        assert len(ADVISOR_SYSTEM_PROMPT) == 1464

    async def test_the_default_prompts_are_sent_and_versioned(self):
        provider = FakeProvider()
        orchestrator = PlutusOrchestrator(provider=provider)

        result, system = await ask(orchestrator, provider)
        assert sha256(system) == CHAT_SHA256
        assert result["metadata"]["prompt_version"] == PACKAGE_DEFAULT_PROMPT_VERSION == "package-default"

        provider._raw_text = "[]"
        result, system = await ask(orchestrator, provider, output_contract="brief")
        assert sha256(system) == BRIEF_SHA256
        assert result["metadata"]["prompt_version"] == "package-default"

    def test_explicitly_naming_the_default_is_allowed(self):
        prompts = resolve_prompts(prompt_version="package-default")
        assert sha256(prompts.chat) == CHAT_SHA256
        assert sha256(prompts.brief) == BRIEF_SHA256


class TestHostPrompt:
    async def test_the_host_prompt_and_version_are_used_and_recorded(self):
        provider = FakeProvider()
        orchestrator = PlutusOrchestrator(provider=provider, system_prompt=HOST_PROMPT,
                                          prompt_version="wealthify-chat-2026-10-05")
        result, system = await ask(orchestrator, provider)

        assert system == HOST_PROMPT
        assert result["success"] is True
        assert result["metadata"]["prompt_version"] == "wealthify-chat-2026-10-05"

    async def test_the_brief_prompt_derives_from_the_host_prompt(self):
        provider = FakeProvider(raw_text="[]")
        orchestrator = PlutusOrchestrator(provider=provider, system_prompt=HOST_PROMPT,
                                          prompt_version="host-v2")
        _, system = await ask(orchestrator, provider, output_contract="brief")
        assert system == "You are the host's evaluated advisor.\n" + BRIEF_CONTRACT

    async def test_an_explicit_brief_prompt_is_used_verbatim(self):
        provider = FakeProvider(raw_text="[]")
        orchestrator = PlutusOrchestrator(provider=provider, system_prompt=HOST_PROMPT,
                                          brief_system_prompt="Host brief policy.",
                                          prompt_version="host-v3")
        _, system = await ask(orchestrator, provider, output_contract="brief")
        assert system == "Host brief policy."

    async def test_failures_still_name_the_prompt_version(self, failing_provider):
        orchestrator = PlutusOrchestrator(provider=failing_provider, system_prompt=HOST_PROMPT,
                                          prompt_version="host-v4")
        result = await orchestrator.process_message("hello", "person", user_context={})
        assert result["success"] is False
        assert result["metadata"]["prompt_version"] == "host-v4"

    async def test_prompt_text_never_reaches_results_or_logs(self, caplog):
        caplog.set_level("DEBUG")
        secret_prompt = "Host policy sentinel-7f3a. Output contract: JSON."
        provider = FakeProvider()
        orchestrator = PlutusOrchestrator(provider=provider, system_prompt=secret_prompt,
                                          prompt_version="host-v5")
        result, _ = await ask(orchestrator, provider)
        assert "sentinel-7f3a" not in json.dumps(result) + caplog.text


class TestValidation:
    @pytest.mark.parametrize("kwargs", [
        {"system_prompt": HOST_PROMPT},                                   # unversioned
        {"system_prompt": HOST_PROMPT, "prompt_version": "package-default"},
        {"brief_system_prompt": "Brief only."},
        {"prompt_version": "host-v1"},                    # a label without a host prompt
        {"system_prompt": "   ", "prompt_version": "host-v1"},
        {"system_prompt": "", "prompt_version": "host-v1"},
        {"system_prompt": b"bytes", "prompt_version": "host-v1"},
        {"system_prompt": HOST_PROMPT, "prompt_version": "has space"},
        {"system_prompt": HOST_PROMPT, "prompt_version": ""},
        {"system_prompt": HOST_PROMPT, "prompt_version": "v" * 65},
        {"system_prompt": HOST_PROMPT, "prompt_version": 2},
        {"system_prompt": "x" * (MAX_SYSTEM_PROMPT_BYTES + 1), "prompt_version": "host-v1"},
        {"system_prompt": "é" * (MAX_SYSTEM_PROMPT_BYTES // 2 + 1), "prompt_version": "host-v1"},
    ])
    def test_invalid_prompt_configuration_is_refused(self, kwargs):
        with pytest.raises(ValueError):
            resolve_prompts(**kwargs)

    def test_the_orchestrator_refuses_before_building_a_provider(self, monkeypatch):
        import plutus.agents.advanced_orchestrator as module

        def forbidden(**kwargs):
            raise AssertionError("provider built for an invalid prompt configuration")

        monkeypatch.setattr(module, "OpenAIProvider", forbidden)
        with pytest.raises(ValueError):
            module.AdvancedOrchestrator(system_prompt=HOST_PROMPT)

    def test_the_largest_allowed_prompts_are_accepted(self):
        prompts = resolve_prompts(system_prompt="x" * MAX_SYSTEM_PROMPT_BYTES,
                                  brief_system_prompt="y" * MAX_SYSTEM_PROMPT_BYTES,
                                  prompt_version="host-v1.2_eval:a")
        assert prompts.version == "host-v1.2_eval:a"
        assert len(prompts.chat) == len(prompts.brief) == MAX_SYSTEM_PROMPT_BYTES

    def test_a_derived_brief_prompt_must_also_fit(self):
        """Without its own contract section the brief appends one, and grows."""
        with pytest.raises(ValueError):
            resolve_prompts(system_prompt="x" * MAX_SYSTEM_PROMPT_BYTES, prompt_version="host-v1")

    def test_the_system_prompt_bound_keeps_input_inside_the_host_reservation(self):
        """Wealthify reserves spend for 32,768 input tokens per attempt.

        A byte-level tokenizer never emits more tokens than bytes, so the user
        prompt ceiling plus the system prompt ceiling must stay below it.
        """
        from plutus.agents.prompt_context import MAX_PROMPT_BYTES

        assert MAX_PROMPT_BYTES + MAX_SYSTEM_PROMPT_BYTES < 32_768

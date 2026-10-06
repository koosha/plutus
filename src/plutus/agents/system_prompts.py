"""System prompts for the synthesis call, and who supplied them.

The package ships one default prompt. A host may supply its own chat prompt,
optionally a separate brief prompt, and a version id for them, so a prompt the
host has evaluated can change without a package release. Every orchestrator
result records the version of the prompt that produced it.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional

PACKAGE_DEFAULT_PROMPT_VERSION = "package-default"

# Every system prompt that is sent is at most this many UTF-8 bytes. A
# byte-level tokenizer never produces more tokens than bytes, so together with
# prompt_context.MAX_PROMPT_BYTES this keeps a request's input below the
# 32,768 input tokens Wealthify reserves spend for on each attempt.
MAX_SYSTEM_PROMPT_BYTES = 8192

_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")

# Educational-scope guardrails + output contract for the synthesis call.
# Every real completion goes through this system prompt unless the host
# supplies its own.
ADVISOR_SYSTEM_PROMPT = """You are Plutus, the AI financial guide inside the Wealthify app.

Strict scope and safety rules:
- Provide educational, general financial information grounded ONLY in the user data supplied in the request. Do not invent numbers that are not present; say plainly when data is missing.
- Missing, withheld, failed or omitted context is unknown, never zero. Respect availability/provenance and prompt_metadata; heuristic findings are limited to their stated evidence and policy.
- Do NOT give individualized investment advice: never recommend buying, selling, or holding any specific security, fund, or asset. Discuss categories, trade-offs, and widely accepted principles instead.
- Never claim to execute trades, move money, open or close accounts, or take any action. You cannot take actions.
- For decisions with tax, legal, or large financial consequences, remind the user to consult a licensed professional.
- Keep a supportive, plain-language tone; be concise.

Output contract — respond with a single JSON object and nothing else (no markdown fences):
{"response": string, "insights": [string, ...], "recommendations": [string, ...], "confidence": number}
- "response": the reply shown to the user (plain text, may use simple bullet lines).
- "insights": up to 5 short observations grounded in the data (may be empty).
- "recommendations": up to 5 short educational next steps (may be empty).
- "confidence": 0..1, your confidence given the data completeness."""

BRIEF_OUTPUT_CONTRACT = (
    "Output contract: return only a JSON array of brief cards with string fields "
    "tone, title, body and action. Return [] if nothing is notable."
)

# A chat prompt's output contract section starts at the one line that begins
# with this phrase and runs to the end of the prompt. A derived brief prompt
# keeps everything before that line and replaces the section.
OUTPUT_CONTRACT_MARKER = "Output contract"
_SECTION_START = re.compile("^" + re.escape(OUTPUT_CONTRACT_MARKER), re.MULTILINE)


def brief_prompt_from(chat_prompt: str) -> str:
    """The brief keeps the chat prompt's rules and replaces its output contract.

    The cut is made at the only line that starts with "Output contract". The
    phrase inside a line belongs to a rule and is kept. With no such line the
    brief would carry the chat contract beside the card contract; with more
    than one, the cut point is ambiguous and could drop the rules between
    them. Either raises ValueError, without quoting the prompt.
    """
    starts = [match.start() for match in _SECTION_START.finditer(chat_prompt)]
    if not starts:
        raise ValueError("The chat system prompt has no line that starts with 'Output "
                         "contract' for the brief contract to replace; supply "
                         "brief_system_prompt")
    if len(starts) > 1:
        raise ValueError("The chat system prompt has more than one line that starts "
                         "with 'Output contract', so the section to replace is "
                         "ambiguous; supply brief_system_prompt")
    return chat_prompt[:starts[0]] + BRIEF_OUTPUT_CONTRACT


@dataclass(frozen=True)
class PromptSet:
    """The prompts one orchestrator sends, and the version that names them."""

    chat: str
    brief: str
    version: str

    def for_contract(self, output_contract: Any) -> str:
        return self.brief if output_contract == "brief" else self.chat


PACKAGE_DEFAULT_PROMPTS = PromptSet(
    chat=ADVISOR_SYSTEM_PROMPT,
    brief=brief_prompt_from(ADVISOR_SYSTEM_PROMPT),
    version=PACKAGE_DEFAULT_PROMPT_VERSION,
)


def _checked(text: Any, name: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{name} must be non-empty text")
    if len(text.encode("utf-8")) > MAX_SYSTEM_PROMPT_BYTES:
        raise ValueError(f"{name} exceeds {MAX_SYSTEM_PROMPT_BYTES} UTF-8 bytes")
    return text


def resolve_prompts(
    system_prompt: Optional[str] = None,
    brief_system_prompt: Optional[str] = None,
    prompt_version: Optional[str] = None,
) -> PromptSet:
    """Validate host-supplied prompts; the package default needs no arguments.

    A host prompt must come with its own version id, and a version id other
    than the package default must come with a host prompt, so results can
    never attribute one prompt's answers to another. A brief prompt is
    derived only from a chat prompt with exactly one line that starts its
    output contract section (see brief_prompt_from); otherwise the host
    supplies brief_system_prompt. Prompt text is never included in an
    error message.
    """
    supplied = system_prompt is not None or brief_system_prompt is not None
    if not supplied:
        if prompt_version not in (None, PACKAGE_DEFAULT_PROMPT_VERSION):
            raise ValueError("prompt_version names a host prompt, but no prompt was supplied")
        return PACKAGE_DEFAULT_PROMPTS
    if not isinstance(prompt_version, str) or not _VERSION.fullmatch(prompt_version):
        raise ValueError("A host system prompt needs a prompt_version of 1-64 letters, "
                         "digits, '.', '_', ':' or '-'")
    if prompt_version == PACKAGE_DEFAULT_PROMPT_VERSION:
        raise ValueError("A host system prompt cannot use the package-default version")
    chat = ADVISOR_SYSTEM_PROMPT if system_prompt is None else _checked(system_prompt, "system_prompt")
    if brief_system_prompt is None:
        brief = _checked(brief_prompt_from(chat), "the brief prompt derived from system_prompt")
    else:
        brief = _checked(brief_system_prompt, "brief_system_prompt")
    return PromptSet(chat=chat, brief=brief, version=prompt_version)

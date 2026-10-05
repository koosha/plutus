"""Versioned prices and the allowed model names.

Expected costs are worked out by hand from the per-million-token list prices
published on 2026-10-04 (input / output, USD):

    gpt-5 1.25 / 10.00     gpt-5-mini 0.25 / 2.00    gpt-5-nano 0.05 / 0.40
    gpt-5.6-luna 0.20 / 1.20   gpt-5.6-terra 2.00 / 12.00   gpt-5.6-sol 4.00 / 20.00
    gpt-6-luna 0.10 / 0.50     gpt-6-sol 2.00 / 10.00

The 5.6 and 6 families also bill input written to the prompt cache, which is
on by default, at 1.25x the uncached input rate (published cache-write
prices: gpt-5.6-luna 0.25, gpt-5.6-terra 2.50, gpt-5.6-sol 5.00, gpt-6-luna
0.125, gpt-6-sol 2.50). The gpt-5 family has no cache-write charge. A price
that must never under-state spend therefore charges each input token at the
highest rate it can be billed: the cache-write rate where one exists.

They are written out as literals so a wrong table entry cannot also produce
the expected value.
"""

import pytest
from provider_transport import TEST_KEY, RecordingHandler, chat_body, provider_over

from plutus.llm import LLMError, LLMModelNotPricedError, LLMNotConfiguredError
from plutus.llm.provider import PRICING_VERSION, cost_for

MILLION = 1_000_000

# (model, highest price of one million input tokens, price of one million
# output tokens). The input price is the cache-write price where the family
# has one (1.25x its 0.20 / 2.00 / 4.00 / 0.10 / 2.00 uncached input price).
PUBLISHED = [
    ("gpt-5", 1.25, 10.00),
    ("gpt-5-mini", 0.25, 2.00),
    ("gpt-5-nano", 0.05, 0.40),
    ("gpt-5.6-luna", 0.25, 1.20),
    ("gpt-5.6-terra", 2.50, 12.00),
    ("gpt-5.6-sol", 5.00, 20.00),
    ("gpt-6-luna", 0.125, 0.50),
    ("gpt-6-sol", 2.50, 10.00),
]


class TestPublishedPrices:
    @pytest.mark.parametrize("model,input_price,output_price", PUBLISHED)
    def test_each_listed_model_prices_input_and_output_separately(
        self, model, input_price, output_price
    ):
        assert cost_for(model, MILLION, 0) == pytest.approx(input_price)
        assert cost_for(model, 0, MILLION) == pytest.approx(output_price)

    def test_a_mixed_request_on_a_candidate_model(self):
        # 12,345 x $2.50/M + 678 x $12.00/M = 0.0308625 + 0.008136
        assert cost_for("gpt-5.6-terra", 12_345, 678) == pytest.approx(0.0389985)

    def test_the_gpt_5_family_has_no_cache_write_charge(self):
        # 12,345 x $0.25/M + 678 x $2.00/M = 0.00308625 + 0.001356
        assert cost_for("gpt-5-mini", 12_345, 678) == pytest.approx(0.00444225)

    def test_the_pricing_version_names_the_new_table(self):
        assert PRICING_VERSION.endswith("-standard-2026-10-04")


class TestAllowedNames:
    @pytest.mark.parametrize(
        "model,family_input_price",
        [
            ("gpt-5.6-terra-2026-10-01", 2.50),
            ("gpt-6-luna-2026-12-31", 0.125),
            ("gpt-5.6-sol-2027-02-28", 5.00),
            ("gpt-6-sol-2026-01-31", 2.50),
            ("gpt-5.6-luna-2026-09-30", 0.25),
            ("gpt-5-mini-2025-08-07", 0.25),
            ("gpt-5-nano-2025-08-07", 0.05),
            ("gpt-5-2025-08-07", 1.25),
        ],
    )
    def test_a_dated_snapshot_prices_like_its_family(self, model, family_input_price):
        assert cost_for(model, MILLION, 0) == pytest.approx(family_input_price)

    @pytest.mark.parametrize(
        "model",
        [
            "gpt-5x6-terra",             # the dot is literal, not "any character"
            "gpt-5.6",                   # a version without a tier
            "gpt-6",
            "gpt-5.6-terra-pro",
            "gpt-5.6-terra-latest",
            "gpt-5.6-terra-20261001",    # suffix must be -YYYY-MM-DD
            "gpt-5.6-terra-2026-13-01",  # no month 13
            "gpt-5.6-terra-2026-10-32",  # no day 32
            "gpt-5.6-terra-2026-10-01-extra",
            "GPT-5.6-TERRA",
            " gpt-5.6-terra",
            "gpt-5.6-terra ",
            "gpt-7-ultra",
            "",
        ],
    )
    def test_unknown_and_malformed_names_have_no_price(self, model):
        assert cost_for(model, MILLION, MILLION) is None

    @pytest.mark.parametrize("model", [None, 5, b"gpt-5-mini"])
    def test_a_non_string_model_has_no_price(self, model):
        assert cost_for(model, MILLION, MILLION) is None


class TestReservationAndRefusal:
    def test_the_reservation_bound_uses_the_candidate_price(self):
        provider = provider_over(RecordingHandler(), model="gpt-5.6-terra")
        # Per attempt: 32,768 x $2.50/M + 1,024 x $12.00/M = 0.08192 + 0.012288
        assert provider.maximum_cost(32_768, 1_024, 4) == pytest.approx(0.376832)

    @pytest.mark.parametrize("model,per_attempt", [
        ("gpt-5.6-luna", 0.0094208),   # 32,768 x 0.25/M + 1,024 x 1.20/M
        ("gpt-5.6-terra", 0.094208),   # 32,768 x 2.50/M + 1,024 x 12.00/M
        ("gpt-5.6-sol", 0.18432),      # 32,768 x 5.00/M + 1,024 x 20.00/M
        ("gpt-6-luna", 0.004608),      # 32,768 x 0.125/M + 1,024 x 0.50/M
        ("gpt-6-sol", 0.09216),        # 32,768 x 2.50/M + 1,024 x 10.00/M
        ("gpt-5-mini", 0.01024),       # 32,768 x 0.25/M + 1,024 x 2.00/M
    ])
    def test_the_reservation_covers_input_written_to_the_cache(self, model, per_attempt):
        """The host reserves this before dispatch; it must be the true ceiling."""
        provider = provider_over(RecordingHandler(), model=model)
        assert provider.maximum_cost(32_768, 1_024) == pytest.approx(per_attempt)

    async def test_a_settled_candidate_cost_never_falls_below_the_bill(self):
        """Settlement charges every input token at the cache-write rate.

        The provider reports 1,024 of 2,048 input tokens read from the cache
        and 1,024 written to it. The bill for that split is 1,024 x $0.01/M +
        1,024 x $0.125/M + 4 x $0.50/M = 0.00014024; the settled cost is
        2,048 x $0.125/M + 4 x $0.50/M = 0.000258, an upper bound.
        """
        provider = provider_over(RecordingHandler(body=chat_body(
            model="gpt-6-luna", prompt_tokens=2_048, completion_tokens=4,
            prompt_tokens_details={"cached_tokens": 1_024, "cache_write_tokens": 1_024},
        )), model="gpt-6-luna")
        completion = await provider.complete([{"role": "user", "content": "hello"}])
        await provider.aclose()

        assert completion.cost == pytest.approx(0.000258)
        assert completion.cost >= 0.00014024

    def test_an_unpriced_model_has_no_reservation_bound(self):
        provider = provider_over(RecordingHandler(), model="gpt-7-ultra")
        assert provider.maximum_cost(32_768, 1_024, 4) is None

    async def test_an_unpriced_model_is_refused_before_any_request(self):
        handler = RecordingHandler()
        provider = provider_over(handler, model="gpt-7-ultra")
        with pytest.raises(LLMModelNotPricedError) as caught:
            await provider.complete([{"role": "user", "content": "hello"}])
        await provider.aclose()

        assert handler.requests == []
        assert isinstance(caught.value, LLMNotConfiguredError)
        assert isinstance(caught.value, LLMError)
        assert caught.value.category == "model_not_priced"
        assert caught.value.retryable is False
        assert "gpt-7-ultra" not in str(caught.value)

    async def test_a_priced_candidate_is_dispatched_with_its_name(self):
        handler = RecordingHandler()
        provider = provider_over(handler, model="gpt-6-luna")
        await provider.complete([{"role": "user", "content": "hello"}])
        await provider.aclose()

        assert [request["model"] for request in handler.requests] == ["gpt-6-luna"]

    def test_constructing_an_unpriced_provider_still_succeeds(self):
        """Hosts read maximum_cost() to refuse; construction stays cheap."""
        from plutus.llm import OpenAIProvider

        assert OpenAIProvider(api_key=TEST_KEY, model="gpt-7-ultra").model == "gpt-7-ultra"

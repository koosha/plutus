"""One reading of annual percentage rates for every specialist (N11).

The recommendation specialist used to compare rates as percentages (> 15)
while the risk specialist compared them as fractions (> 0.20), so the same
account was high-interest to one and not the other. Each specialist keeps
its own threshold (15% and 20% APR); only the unit is unified.
"""

import math

import pytest

from plutus.agents.boundaries import apr_fraction
from plutus.agents.recommendation_agent import RecommendationAgent
from plutus.agents.risk_assessment_agent import RiskAssessmentAgent


class TestAprFraction:
    @pytest.mark.parametrize("value,expected", [
        (24.99, 0.2499),     # percentage
        (0.2499, 0.2499),    # fraction
        (18, 0.18),
        (400, 4.0),          # payday-loan scale is still a percentage
        (0, 0.0),            # promotional 0% is known, not missing
        (1, 1.0),            # boundary: 1 is not greater than 1, so a fraction
        (1.000001, 0.01000001),
    ])
    def test_without_a_unit_values_above_one_are_percentages(self, value, expected):
        assert apr_fraction(value) == pytest.approx(expected)

    @pytest.mark.parametrize("value,unit,expected", [
        (0.5, "percent", 0.005),
        (24.99, "percent", 0.2499),
        (24.99, "fraction", 24.99),
        (0.2, "fraction", 0.2),
        (1, "percent", 0.01),
    ])
    def test_an_explicit_unit_wins(self, value, unit, expected):
        assert apr_fraction(value, unit) == pytest.approx(expected)

    @pytest.mark.parametrize("value,unit", [
        (None, None), (-1, None), (-0.01, "fraction"), ("24", None), (True, None),
        (math.nan, None), (math.inf, None), (5, "basis_points"), (5, "Percent"),
    ])
    def test_missing_invalid_and_unrecognised_rates_are_unknown(self, value, unit):
        assert apr_fraction(value, unit) is None


def debt_context(rate, unit=None, balance=-3000):
    card = {"type": "credit_card", "balance": balance, "currency": "USD", "interest_rate": rate}
    if unit is not None:
        card["interest_rate_unit"] = unit
    return {"monthly_income": 5000,
            "accounts": [{"type": "checking", "balance": 2000, "currency": "USD"}, card]}


async def recommends_high_interest_focus(context):
    recommendations = await RecommendationAgent()._generate_debt_recommendations(context)
    return "high_interest_debt_focus" in [item["id"] for item in recommendations]


async def high_interest_debt(context):
    return (await RiskAssessmentAgent()._assess_debt_risk(context))["high_interest_debt"]


class TestRecommendationSpecialist:
    @pytest.mark.parametrize("rate,unit,expected", [
        (0.24, None, True),        # a fraction used to be read as 0.24% and missed
        (24, None, True),
        (15.5, None, True),
        (15, None, False),         # threshold is strictly above 15% APR
        (0.15, None, False),
        (0.1501, None, True),
        (0.5, "percent", False),
        (0.2, "fraction", True),
    ])
    async def test_high_interest_debt_is_found_on_either_scale(self, rate, unit, expected):
        assert await recommends_high_interest_focus(debt_context(rate, unit)) is expected


class TestRiskSpecialist:
    @pytest.mark.parametrize("rate,unit,expected", [
        (18, None, 0),             # 18% used to be read as 1,800% and flagged
        (24.99, None, 3000),
        (0.2499, None, 3000),
        (20, None, 0),             # threshold is strictly above 20% APR
        (0.20, None, 0),
        (20.01, None, 3000),
        (0.5, "percent", 0),
        (25, "percent", 3000),
    ])
    async def test_high_interest_debt_is_measured_on_either_scale(self, rate, unit, expected):
        assert await high_interest_debt(debt_context(rate, unit)) == expected

    @pytest.mark.parametrize("rate,unit", [(None, None), (-5, None), (12, "basis_points")])
    async def test_an_unusable_rate_leaves_debt_risk_unknown(self, rate, unit):
        result = await RiskAssessmentAgent()._assess_debt_risk(debt_context(rate, unit))
        assert result["score"] is None
        assert result["missing_inputs"] == ["debt_interest_rates"]

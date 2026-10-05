"""Specialist logs carry progress, never a user's financial results."""

import logging

from plutus.agents.risk_assessment_agent import RiskAssessmentAgent

SENTINEL_SCORE = 61.4321


async def test_the_risk_score_is_not_logged(caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    agent = RiskAssessmentAgent()

    async def planted_score(assessment):
        return SENTINEL_SCORE

    monkeypatch.setattr(agent, "_calculate_overall_risk_score", planted_score)
    result = await agent.process({"user_message": "How risky is my situation?",
                                  "user_context": {"monthly_income": 5000, "accounts": []}})

    assert result["success"] is True
    assert result["analysis"]["overall_risk_score"] == SENTINEL_SCORE
    assert "61.4321" not in caplog.text
    assert "risk score" not in caplog.text.lower()
    # Progress logging remains.
    assert any("Risk Assessment Agent" in record.getMessage() for record in caplog.records)

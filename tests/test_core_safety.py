"""Regression checks for result, execution, context and configuration boundaries."""
import asyncio
import json
import math

import pytest

from plutus.agents.base_agent import BaseAgent
from plutus.agents.advanced_orchestrator import AdvancedOrchestrator
from plutus.agents.mixins import TextParsingMixin
from plutus.core.config import PlutusConfig
from plutus.models.state import UserContext
from plutus.services.context_service import ContextService


class StubAgent(BaseAgent):
    async def _process_core_logic(self, state):
        if state.get('raise'):
            raise ValueError('synthetic-secret-token')
        return state['result']


@pytest.mark.asyncio
async def test_returned_failure_remains_failed_and_is_counted(caplog):
    agent = StubAgent()
    result = await agent.process({'result': {'success': False, 'error': 'synthetic-secret-token'}})
    assert result['success'] is False
    assert agent.total_errors == 1
    assert result['error_type'] == 'agent_error'
    assert result['request_id']
    assert 'synthetic-secret-token' not in json.dumps(result) + caplog.text


@pytest.mark.asyncio
async def test_exception_and_malformed_results_are_safe_failures(caplog):
    agent = StubAgent()
    for state in ({'raise': True}, {'result': []}, {'result': {'success': 'false'}}, {'result': {}}):
        result = await agent.process(state)
        assert result['success'] is False
        assert result['request_id']
        assert 'synthetic-secret-token' not in json.dumps(result) + caplog.text
    assert agent.total_errors == 4
    assert agent.total_execution_time > 0


@pytest.mark.asyncio
async def test_cancellation_propagates():
    agent = StubAgent()
    async def cancelled(state):
        raise asyncio.CancelledError()
    agent._process_core_logic = cancelled
    with pytest.raises(asyncio.CancelledError):
        await agent.process({})
    assert agent.total_execution_time > 0


@pytest.mark.parametrize('field,value', [
    ('request_timeout', math.nan), ('request_timeout', math.inf),
    ('agent_timeout_seconds', 0), ('max_parallel_agents', 0),
    ('max_parallel_agents', True), ('max_retries', -1),
    ('max_output_tokens', 0), ('llm_temperature', math.nan),
])
def test_invalid_constructor_settings_rejected(field, value):
    with pytest.raises(ValueError):
        PlutusConfig(**{field: value})


@pytest.mark.parametrize('key', ['PLUTUS_REQUEST_TIMEOUT', 'PLUTUS_AGENT_TIMEOUT'])
@pytest.mark.parametrize('value', ['nan', 'inf', '-inf', '0'])
def test_nonfinite_environment_uses_safe_default(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    config = PlutusConfig()
    assert config.request_timeout == 30
    assert config.agent_timeout_seconds == 30
    assert math.isfinite(config.llm_deadline_seconds)


def test_amount_parser_handles_suffixes_once_and_ignores_timeframes():
    message = 'Save $50k, 2 million dollars and $75.50 in 2 years; 100 dollars now.'
    expected = [50000, 2000000, 75.5, 100]
    assert StubAgent().extract_financial_amounts(message) == expected
    assert TextParsingMixin().extract_financial_amounts(message) == expected


@pytest.mark.asyncio
async def test_context_does_not_invent_conversation_history():
    context = UserContext(user_id='person')
    result = await ContextService()._enhance_with_conversation_insights(context)
    assert result.recent_topics == []
    assert result.common_questions == []


def test_bounded_prompt_is_valid_json_preserves_essential_context(fake_provider):
    orchestrator = AdvancedOrchestrator(provider=fake_provider)
    context = {
        'goals': [{'description': '💰' * 10000, 'target': 20000}] * 500,
        'accounts': [{'balance': 100, 'name': 'account' * 1000}] * 500,
        'financial_snapshot': {'net_worth': 100, 'monthly_income': None},
        'consent': {'accounts': False}, 'availability': {'accounts': 'withheld'},
        'provenance': {'source': 'host', 'as_of': '2026-09-10'},
    }
    prompt = orchestrator._compose_synthesis_prompt(
        {'user_message': 'Question ' + '💰' * 10000, 'user_context': context},
        {'agent_results': [{'success': True, 'analysis': {'details': 'x' * 20000}}] * 500},
    )
    assert len(prompt.encode('utf-8')) <= 24000
    parsed = json.loads(prompt)
    assert parsed['financial_context']['financial_snapshot'] == context['financial_snapshot']
    assert parsed['financial_context']['consent'] == context['consent']
    assert parsed['financial_context']['availability'] == context['availability']
    assert parsed['financial_context']['provenance'] == context['provenance']
    assert parsed['prompt_metadata']['omitted_items'] > 0


@pytest.mark.asyncio
async def test_selected_specialists_have_same_results_on_both_executors(fake_provider):
    orchestrator = AdvancedOrchestrator(provider=fake_provider)
    calls = []
    async def run(name, state):
        calls.append(name)
        return {'agent_name': name, 'agent_type': name, 'success': name != 'risk_assessment', 'response': ''}
    orchestrator._run_agent = run
    state = {'user_message': 'help', 'user_context': {}}
    routing = {'agents_to_run': ['financial_analysis', 'goal_extraction', 'risk_assessment', 'recommendation'], 'execution_strategy': 'parallel'}
    minimal = await orchestrator._execute_fallback_workflow(state, routing)
    first_calls = calls[:]
    calls.clear()
    # Exercise the graph node even where LangGraph is an optional dependency.
    class Workflow:
        async def ainvoke(self, graph_state):
            return await orchestrator._langgraph_execute_plan(graph_state)
    orchestrator.workflow = Workflow()
    graph = await orchestrator._execute_langgraph_workflow(state, routing)
    assert first_calls == calls == routing['agents_to_run']
    assert minimal['agent_results'] == graph['agent_results']
    assert minimal['metadata']['successful_agents'] == graph['metadata']['successful_agents'] == 3
    assert minimal['metadata']['partial'] is graph['metadata']['partial'] is True


@pytest.mark.asyncio
async def test_missing_personal_facts_and_finances_stay_unknown():
    from plutus.agents.risk_assessment_agent import RiskAssessmentAgent
    from plutus.agents.financial_analysis_agent import FinancialAnalysisAgent
    from plutus.agents.goal_extraction_agent import GoalExtractionAgent
    from plutus.agents.recommendation_agent import RecommendationAgent
    context = {'net_worth': None, 'monthly_income': None, 'monthly_expenses': None,
               'wealth_health_score': None, 'accounts': [], 'holdings': [],
               'data_provenance': {'accounts': {'availability': 'withheld'},
                                   'holdings': {'availability': 'withheld'}}}
    state = {'user_message': 'help me plan retirement and assess risk', 'user_context': context}
    risk = await RiskAssessmentAgent().process(state)
    assert risk['success'] is True
    assert risk['analysis']['overall_risk_score'] is None
    assert risk['analysis']['risk_profile'] == 'unknown'
    assert risk['risk_assessment']['income_risk']['employment_type'] is None
    insurance = risk['risk_assessment']['insurance_risk']
    assert insurance['score'] is None
    assert insurance['has_health_insurance'] is None
    assert insurance['has_disability_insurance'] is None
    assert insurance['factors'] == []
    assert risk['risk_assessment']['investment_risk']['concentration_risk'] is None
    financial = await FinancialAnalysisAgent().process(state)
    assert financial['success'] is True
    assert financial['analysis']['net_worth'] is None
    assert financial['analysis']['monthly_savings'] is None
    assert financial['analysis']['emergency_fund_months'] is None
    assert financial['analysis']['debt_analysis']['has_debt'] is None
    assert financial['recommendations'] == []
    goals = await GoalExtractionAgent().process(state)
    recommendations = await RecommendationAgent().process(state)
    assert goals['success'] is recommendations['success'] is True
    assert goals['analysis']['recommendations'] == []
    assert [item['id'] for item in recommendations['recommendations']] == ['set_financial_goals']
    public = json.dumps([risk, financial, goals, recommendations])
    for invented in ('age 30', 'full_time', 'No disability insurance coverage', 'doing well overall'):
        assert invented not in public


@pytest.mark.asyncio
async def test_actual_holdings_concentration_combines_duplicate_securities():
    from plutus.agents.risk_assessment_agent import RiskAssessmentAgent
    context = {'holdings': [
        {'symbol': 'A', 'value': 20, 'currency': 'USD'},
        {'symbol': 'A', 'value': 20, 'currency': 'USD'},
        {'symbol': 'B', 'value': 20, 'currency': 'USD'},
        {'symbol': 'C', 'value': 20, 'currency': 'USD'},
        {'symbol': 'D', 'value': 20, 'currency': 'USD'},
    ]}
    agent = RiskAssessmentAgent()
    result = await agent._assess_investment_risk(context)
    assert result['largest_holding_percentage'] == 0.4
    assert result['concentration_risk'] is True
    context['holdings'][0]['currency'] = 'EUR'
    unknown = await agent._assess_investment_risk(context)
    assert unknown['score'] is None
    assert unknown['concentration_risk'] is None


@pytest.mark.asyncio
async def test_actual_cash_debt_and_expenses_replace_invented_percentages():
    from plutus.agents.financial_analysis_agent import FinancialAnalysisAgent
    context = {'net_worth': 100000, 'monthly_income': 5000, 'monthly_expenses': 2000,
               'accounts': [{'balance': 4000, 'type': 'checking', 'currency': 'USD'},
                            {'balance': -12000, 'type': 'loan', 'currency': 'USD'}]}
    result = await FinancialAnalysisAgent().process({'user_context': context})
    assert result['success'] is True
    assert result['analysis']['emergency_fund_months'] == 2
    assert result['analysis']['debt_analysis']['total_debt'] == 12000
    assert result['analysis']['savings_rate'] == 0.6


@pytest.mark.asyncio
async def test_partial_measurement_does_not_override_unknown_with_a_subtotal():
    from plutus.agents.financial_analysis_agent import FinancialAnalysisAgent
    context = {'monthly_income': 5000, 'monthly_expenses': 2000, 'net_worth': 100000,
               'financial_measurements': {'net_worth': {'complete': False, 'total': 100000, 'currency': 'USD'},
                                          'income': {'complete': False, 'total': 5000, 'currency': 'USD'}},
               'accounts': [{'balance': 4000, 'type': 'checking', 'currency': 'EUR'}]}
    result = await FinancialAnalysisAgent().process({'user_context': context})
    assert result['success'] is True
    assert result['analysis']['net_worth'] is None
    assert result['analysis']['savings_rate'] is None
    assert result['analysis']['emergency_fund_months'] is None


@pytest.mark.asyncio
async def test_provider_secrets_never_enter_results_or_logs(caplog):
    from conftest import FakeProvider
    from plutus.llm import LLMResponseError
    orchestrator = AdvancedOrchestrator(provider=FakeProvider(error=LLMResponseError('synthetic-secret-token')))
    result = await orchestrator.process_message('question', 'person', user_context={})
    assert result['success'] is False
    assert result['error_type'] == 'llm_error'
    assert 'synthetic-secret-token' not in json.dumps(result) + caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['{}', '{"insights": []}', '[]', '{broken'])
async def test_malformed_completion_cannot_become_empty_success(text):
    from conftest import FakeProvider
    result = await AdvancedOrchestrator(provider=FakeProvider(raw_text=text)).process_message('hello', 'person', user_context={})
    assert result['success'] is False
    assert result['error_type'] == 'llm_error'


@pytest.mark.asyncio
async def test_parallel_cancellation_cancels_all_specialists(fake_provider):
    orchestrator = AdvancedOrchestrator(provider=fake_provider)
    started = set()
    stopped = set()
    ready = asyncio.Event()
    async def run(name, state):
        started.add(name)
        if len(started) == 4:
            ready.set()
        try:
            await asyncio.sleep(20)
        finally:
            stopped.add(name)
    orchestrator._run_agent = run
    routing = {'agents_to_run': ['financial_analysis', 'goal_extraction', 'risk_assessment', 'recommendation'], 'execution_strategy': 'parallel'}
    task = asyncio.create_task(orchestrator._execute_fallback_workflow({}, routing))
    await asyncio.wait_for(ready.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stopped == started


@pytest.mark.asyncio
@pytest.mark.parametrize('message', ['net worth', 'goal save for', 'risk', 'invest stocks allocation', 'help me'])
async def test_installed_graph_executes_the_same_selected_plan(message, fake_provider):
    import plutus.agents.advanced_orchestrator as module
    if not module.LANGGRAPH_AVAILABLE:
        pytest.skip('Optional LangGraph mode is verified in the graph CI matrix')
    orchestrator = AdvancedOrchestrator(provider=fake_provider)
    routing = await orchestrator._analyze_conversation_routing(message, {})
    calls = []
    async def run(name, state):
        calls.append(name)
        return {'agent_name': name, 'agent_type': name, 'success': True, 'response': ''}
    orchestrator._run_agent = run
    minimal = await orchestrator._execute_fallback_workflow({}, routing)
    first_calls = calls[:]
    calls.clear()
    graph = await orchestrator._execute_langgraph_workflow({}, routing)
    assert first_calls == calls == routing['agents_to_run']
    assert minimal['agent_results'] == graph['agent_results']
    for key in ('successful_agents', 'agents_run', 'partial', 'execution_strategy'):
        assert minimal['metadata'][key] == graph['metadata'][key]


@pytest.mark.asyncio
async def test_goal_parser_does_not_treat_years_as_target_amounts():
    from plutus.agents.goal_extraction_agent import GoalExtractionAgent
    agent = GoalExtractionAgent()
    goals = await agent._extract_goals_from_text('Save for a house in 2 years with a $50k down payment')
    assert goals
    assert all(goal['target_amount'] == 50000 for goal in goals)


@pytest.mark.asyncio
async def test_synthesis_failure_retains_specialist_failures():
    from conftest import FakeProvider
    from plutus.llm import LLMResponseError
    orchestrator = AdvancedOrchestrator(provider=FakeProvider(error=LLMResponseError('private-secret')))
    async def failed(state):
        return {'success': False, 'error': 'synthetic-secret-token'}
    orchestrator.financial_agent._process_core_logic = failed
    result = await orchestrator.process_message('net worth', 'person', user_context={})
    assert result['success'] is False
    assert result['agent_results'][0]['success'] is False
    assert result['metadata']['successful_agents'] == 0
    assert 'synthetic-secret-token' not in json.dumps(result)
    assert 'private-secret' not in json.dumps(result)


@pytest.mark.asyncio
async def test_revoked_sources_override_lingering_records():
    from plutus.agents.risk_assessment_agent import RiskAssessmentAgent
    context = {'holdings': [{'symbol': 'A', 'value': 10000, 'currency': 'USD'}],
               'data_provenance': {'holdings': {'availability': 'withheld'}}}
    result = await RiskAssessmentAgent()._assess_investment_risk(context)
    assert result['score'] is None
    assert result['concentration_risk'] is None


@pytest.mark.asyncio
async def test_explicit_false_insurance_is_distinct_from_unknown():
    from plutus.agents.risk_assessment_agent import RiskAssessmentAgent
    agent = RiskAssessmentAgent()
    result = await agent._assess_insurance_risk({'has_health_insurance': False})
    assert result['has_health_insurance'] is False
    assert result['has_life_insurance'] is None
    assert result['factors'] == ['No health insurance reported']
    assert result['score'] is None


@pytest.mark.parametrize('kwargs', [{'timeout': math.inf}, {'timeout': 0}, {'max_retries': -1}, {'max_retries': True}])
def test_provider_rejects_invalid_limits_before_constructing_sdk(kwargs):
    from plutus.llm import OpenAIProvider
    with pytest.raises(ValueError):
        OpenAIProvider(api_key='synthetic-key', **kwargs)


@pytest.mark.asyncio
async def test_provider_rejects_bad_completion_limits_before_upstream():
    from plutus.llm import OpenAIProvider
    from unittest.mock import AsyncMock
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider._client = AsyncMock()
    with pytest.raises(ValueError):
        await provider.complete([], max_output_tokens=0)
    with pytest.raises(ValueError):
        await provider.complete([], temperature=math.nan)
    provider._client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_liability_types_and_depository_subtypes_follow_host_contract():
    from plutus.agents.financial_analysis_agent import FinancialAnalysisAgent
    context = {'monthly_income': 5000, 'monthly_expenses': 2000,
               'accounts': [{'balance': 4000, 'type': 'depository', 'subtype': 'checking', 'currency': 'USD'},
                            {'balance': 12000, 'type': 'loan', 'currency': 'USD'},
                            {'balance': -2000, 'type': 'depository', 'subtype': 'checking', 'currency': 'USD'}]}
    result = await FinancialAnalysisAgent().process({'user_context': context})
    assert result['success'] is True
    assert result['analysis']['emergency_fund_months'] == 2
    assert result['analysis']['debt_analysis']['total_debt'] == 12000


def test_extremely_large_limit_is_a_configuration_error():
    with pytest.raises(ValueError):
        PlutusConfig(max_retries=10**1000)

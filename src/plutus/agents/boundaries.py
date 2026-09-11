"""Shared result, amount and evidence boundaries for financial specialists."""
import math
import re
from uuid import uuid4


ERROR_MESSAGES = {
    'agent_error': 'A financial analysis could not be completed.',
    'agent_contract_error': 'A financial analysis returned an invalid result.',
    'agent_timeout': 'A financial analysis exceeded its time limit.',
    'llm_not_configured': 'The response provider is not configured.',
    'llm_error': 'The response provider could not complete the request.',
    'orchestration_error': 'The request could not be completed.',
}


def failure(code='agent_error'):
    """Only stable public messages leave the execution boundary."""
    code = code if code in ERROR_MESSAGES else 'agent_error'
    return {'success': False, 'error_type': code, 'error': ERROR_MESSAGES[code],
            'response': ERROR_MESSAGES[code], 'request_id': uuid4().hex}


def number(value):
    """Return a finite measurement, preserving missing/invalid values as unknown."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def measurement(context, key):
    """Read the canonical snapshot with legacy top-level compatibility."""
    domain = {'net_worth': 'net_worth', 'monthly_income': 'income', 'monthly_expenses': 'expenses'}.get(key)
    measured = context.get('financial_measurements', {}).get(domain)
    if isinstance(measured, dict):
        if measured.get('complete') is not True or measured.get('currency') != 'USD':
            return None
        return number(measured.get('total'))
    snapshot = context.get('financial_snapshot')
    if isinstance(snapshot, dict) and key in snapshot:
        return number(snapshot[key])
    return number(context.get(key))


_AMOUNT = re.compile(
    r'(?<![\w.])(?P<currency>\$\s*)?(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)'
    r'\s*(?P<scale>thousand|million|[km])?(?:\s*(?P<dollars>dollars?))?(?!\w)',
    re.IGNORECASE,
)


def financial_amounts(text):
    """Parse explicit dollar amounts and k/m amounts once, in textual order.

    Unqualified numbers are not amounts: years, ages and goal counts must
    not become money. Multipliers belong to their own match, never the text.
    """
    amounts = []
    for match in _AMOUNT.finditer(text):
        if not any(match.group(key) for key in ('currency', 'scale', 'dollars')):
            continue
        value = float(match.group('number').replace(',', ''))
        scale = (match.group('scale') or '').lower()
        value *= {'k': 1000, 'thousand': 1000, 'm': 1000000, 'million': 1000000}.get(scale, 1)
        if math.isfinite(value):
            amounts.append(value)
    return amounts


def known_accounts(context):
    """Only complete, same-currency account data supports USD calculations."""
    provenance = context.get('data_provenance', {}).get('accounts', {})
    if provenance.get('availability') in ('withheld', 'failed', 'unavailable'):
        return None
    accounts = context.get('accounts')
    if not isinstance(accounts, list):
        return None
    if any(not isinstance(item, dict) or item.get('currency') != 'USD'
           or number(item.get('balance')) is None for item in accounts):
        return None
    return accounts


def unknown_assessment(*missing):
    return {'score': None, 'risk_level': 'unknown', 'factors': [],
            'availability': 'insufficient_evidence', 'missing_inputs': list(missing),
            'policy_version': 'risk-heuristics-v1'}


def is_liability(account):
    """Provider balances retain their sign; account type identifies debt."""
    return account.get('type') in ('credit', 'loan', 'credit_card', 'mortgage', 'liability')


def is_liquid(account):
    return (account.get('type') in ('checking', 'savings') or
            account.get('type') == 'depository' and account.get('subtype') in ('checking', 'savings', 'cash management'))

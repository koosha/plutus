"""Select bounded structured context before JSON serialization."""
import json
import math

MAX_PROMPT_BYTES = 24000
# Priority data must survive large collections that precede it in host input.
_PRIORITY = ('consent', 'availability', 'data_provenance', 'provenance', 'financial_measurements', 'as_of', 'last_data_sync', 'timestamp',
             'currency', 'financial_snapshot', 'net_worth', 'monthly_income',
             'monthly_expenses', 'wealth_health_score', 'account_summary')


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def compose_prompt(message, context, findings, output_tokens):
    omissions = {'omitted_items': 0, 'shortened_strings': 0, 'invalid_values': 0}

    def bounded(value, budget, depth=0):
        if depth > 8:
            omissions['omitted_items'] += 1
            return None
        if value is None or isinstance(value, (bool, int, float)):
            if isinstance(value, float) and not math.isfinite(value):
                omissions['invalid_values'] += 1
                return None
            return value
        if isinstance(value, str):
            # JSON escaping also consumes the budget. Binary search avoids
            # repeatedly copying a large user string one character at a time.
            lo, hi = 0, min(len(value), 3000, budget)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if len(_json(value[:mid]).encode('utf-8')) <= budget:
                    lo = mid
                else:
                    hi = mid - 1
            if lo < len(value):
                omissions['shortened_strings'] += 1
            return value[:lo]
        if isinstance(value, dict):
            selected = {}
            keys = [key for key in _PRIORITY if key in value]
            keys.extend(key for key in value if key not in _PRIORITY)
            for index, key in enumerate(keys):
                if not isinstance(key, str) or len(key) > 100:
                    omissions['omitted_items'] += 1
                    continue
                remaining = budget - len(_json(selected).encode('utf-8')) - len(_json(key).encode('utf-8')) - 3
                if index >= 40 or remaining < 16:
                    omissions['omitted_items'] += 1
                    continue
                item = bounded(value[key], min(remaining, budget // 2), depth + 1)
                candidate = {**selected, key: item}
                if len(_json(candidate).encode('utf-8')) <= budget:
                    selected[key] = item
                else:
                    omissions['omitted_items'] += 1
            return selected
        if isinstance(value, (list, tuple)):
            selected = []
            for index, item in enumerate(value):
                remaining = budget - len(_json(selected).encode('utf-8')) - 2
                if index >= 20 or remaining < 16:
                    omissions['omitted_items'] += len(value) - index
                    break
                item = bounded(item, min(remaining, max(64, budget // 4)), depth + 1)
                if len(_json(selected + [item]).encode('utf-8')) <= budget:
                    selected.append(item)
                else:
                    omissions['omitted_items'] += 1
            return selected
        # Do not stringify arbitrary objects: repr may reveal secrets.
        omissions['invalid_values'] += 1
        return None

    payload = {
        'user_message': bounded(message, 3500),
        'financial_context': bounded(context, 14000),
        'specialist_findings': bounded(findings, 5000),
        'prompt_metadata': {**omissions, 'input_budget_bytes': MAX_PROMPT_BYTES,
                            'reserved_output_tokens': output_tokens},
    }
    prompt = _json(payload)
    # Independent section ceilings reserve envelope/metadata space. A final
    # check fails explicitly if that invariant changes in future edits.
    if len(prompt.encode('utf-8')) > MAX_PROMPT_BYTES:
        raise ValueError('Structured prompt exceeded its input budget')
    return prompt

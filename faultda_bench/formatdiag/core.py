"""Single-decision interface diagnostics. Never execute returned actions."""
import hashlib
import json
import math
import time
import urllib.request

from ..pilot.client import Client as FrozenClient
from ..pilot.contract import messages, valid_decision


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def body(observation, cell):
    request = {'model': 'deepseek-flash', 'temperature': 0,
               'max_tokens': cell['max_tokens'], 'thinking': {'type': cell['thinking']},
               'response_format': {'type': 'json_object'}, 'messages': messages(observation)}
    if cell['thinking'] == 'enabled':
        request['reasoning_effort'] = 'low'
    return request


def classify(answer):
    """Store only safe structure, hashes, valid actions and provider metadata."""
    result = {'category': 'response_shape', 'finish_reason': None, 'length_finish': False,
              'content_bytes': None, 'content_sha256': None, 'reasoning_bytes': None,
              'decision': None}
    if not isinstance(answer, dict):
        return result
    result.update(model=answer.get('model') if isinstance(answer.get('model'), str) else None,
                  response_id=answer.get('id') if isinstance(answer.get('id'), str) else None,
                  usage=answer.get('usage') if isinstance(answer.get('usage'), dict) else {})
    choices = answer.get('choices')
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return result
    choice = choices[0]
    finish = choice.get('finish_reason')
    result['finish_reason'] = finish if finish in ('stop', 'length', 'content_filter', 'tool_calls', 'insufficient_system_resource') else None
    result['length_finish'] = finish == 'length'
    message = choice.get('message')
    if not isinstance(message, dict):
        return result
    reasoning = message.get('reasoning_content')
    if isinstance(reasoning, str):
        result['reasoning_bytes'] = len(reasoning.encode('utf-8'))
    content = message.get('content')
    if content is None:
        result['category'] = 'empty_content'
        return result
    if not isinstance(content, str):
        return result
    raw = content.encode('utf-8')
    result.update(content_bytes=len(raw), content_sha256=sha_bytes(raw))
    if not content.strip():
        result['category'] = 'empty_content'
        return result
    def reject_constant(value):
        raise ValueError('nonfinite JSON')
    def unique_keys(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('duplicate JSON key')
            obj[key] = value
        return obj
    try:
        decision = json.loads(content, parse_constant=reject_constant, object_pairs_hook=unique_keys)
        # Also reject numerical overflow such as 1e999 in otherwise valid JSON.
        json.dumps(decision, allow_nan=False)
    except (ValueError, TypeError):
        result['category'] = 'json_error'
        return result
    result['category'] = 'valid_action' if valid_decision(decision) else 'schema_error'
    if result['category'] == 'valid_action':
        result['decision'] = decision
    return result


class Client(FrozenClient):
    def request_once(self, observation, cell):
        payload = json.dumps(body(observation, cell), ensure_ascii=False, allow_nan=False).encode('utf-8')
        base = {'request_sha256': sha_bytes(payload), 'request_bytes': len(payload)}
        if len(payload) > 65536:
            return {**base, 'category': 'input_limit', 'request_sent': False}
        with self._lock:
            if self.calls >= self.max_calls:
                return {**base, 'category': 'request_cap', 'request_sent': False}
            self.calls += 1
        request = urllib.request.Request('https://api.deepseek.com/chat/completions', data=payload,
                                        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        start = time.perf_counter()
        try:
            result = classify(self.transport(request))
        except Exception as error:
            result = {'category': 'provider_error', 'error_type': type(error).__name__,
                      'http_status': getattr(error, 'code', None)}
        return {**base, **result, 'request_sent': True, 'seconds': time.perf_counter() - start}


def summarize(rows):
    categories = ('valid_action', 'empty_content', 'json_error', 'schema_error', 'response_shape',
                  'provider_error', 'input_limit', 'request_cap')
    sent = [r for r in rows if r['request_sent'] is True]
    usage = [r['usage'] for r in sent if isinstance(r.get('usage'), dict)
             and all(type(r['usage'].get(k)) is int for k in ('prompt_tokens', 'completion_tokens'))]
    arms = {}
    for thinking in ('disabled', 'enabled'):
        for tokens in (800, 2048):
            selected = [r for r in rows if r['thinking'] == thinking and r['max_tokens'] == tokens]
            arms[f'{thinking}_{tokens}'] = {
                'planned': len(selected), 'sent': sum(r['request_sent'] is True for r in selected),
                'categories': {c: sum(r['category'] == c for r in selected) for c in categories},
                'length_finish': sum(r.get('length_finish') is True for r in selected)}
    return {'arms': arms, 'request_attempts': len(sent), 'usage_available_calls': len(usage),
            'reported_prompt_tokens': sum(u['prompt_tokens'] for u in usage) if usage else None,
            'reported_completion_tokens': sum(u['completion_tokens'] for u in usage) if usage else None,
            'actual_models': sorted({r['model'] for r in sent if isinstance(r.get('model'), str)}),
            'scientific_gate': 'HOLD', 'recovery_or_rl_claim': False}

import json
import time
import threading
import urllib.request

from .contract import MAX_PROMPT_BYTES, messages, prompt_bytes, valid_decision


class Client:
    """No implicit retries. An injectable transport supports network-free tests."""
    def __init__(self, model, max_calls=96, *, transport=None, config=None):
        if type(max_calls) is not int or not 1 <= max_calls <= 96:
            raise ValueError('max_calls must be 1..96')
        if config is None:
            from agent.deepseek_config import settings
            config = settings()
        key = config.get('DEEPSEEK_API_KEY', '').strip()
        if not key or key in ('replace_with_your_key', 'your_key', 'YOUR_API_KEY'):
            raise RuntimeError('DeepSeek credential not configured')
        self.key, self.model, self.max_calls, self.calls = key, model, max_calls, 0
        self._lock = threading.Lock()
        self.transport = transport or self._send

    @staticmethod
    def _send(request):
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)

    def choose(self, observation):
        encoded = prompt_bytes(observation)
        if len(encoded) > MAX_PROMPT_BYTES:
            return None, {'error': 'input_limit', 'request_sent': False}
        with self._lock:
            if self.calls >= self.max_calls:
                return None, {'error': 'pilot_call_cap', 'request_sent': False}
            self.calls += 1
        body = {'model': self.model, 'temperature': 0, 'max_tokens': 800,
                'response_format': {'type': 'json_object'}, 'messages': messages(observation)}
        request = urllib.request.Request('https://api.deepseek.com/chat/completions',
                                        data=json.dumps(body).encode(), method='POST',
                                        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        start = time.perf_counter()
        try:
            answer = self.transport(request)
            metadata = {'request_sent': True, 'usage': answer.get('usage', {}),
                        'model': answer.get('model'), 'response_id': answer.get('id'),
                        'seconds': time.perf_counter() - start, 'input_bytes': len(encoded)}
            try:
                choice = json.loads(answer['choices'][0]['message']['content'])
                if not valid_decision(choice):
                    raise ValueError('invalid action schema')
                return choice, metadata
            except (KeyError, IndexError, TypeError, ValueError):
                return {'action': 'invalid_model_output', 'params': {}}, {**metadata, 'parse_error': True}
        except Exception as error:
            # No provider response text or exception message is persisted.
            return None, {'error': type(error).__name__, 'http_status': getattr(error, 'code', None),
                          'seconds': time.perf_counter() - start, 'request_sent': True}

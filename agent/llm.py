import json, os

def parse_json_object(text):
    try: return json.loads(text)
    except json.JSONDecodeError:
        start=text.find("{")
        while start >= 0:
            try: return json.JSONDecoder().raw_decode(text[start:])[0]
            except json.JSONDecodeError: start=text.find("{", start+1)
        raise ValueError("LLM did not return a JSON object")

class LLMClient:
    """OpenAI-compatible adapter for DeepSeek by default, with OpenAI fallback."""
    def __init__(self, model=None, provider=None, temperature=None):
        self.provider=provider or os.getenv("LLM_PROVIDER", "deepseek")
        prefix="DEEPSEEK" if self.provider == "deepseek" else "OPENAI"
        self.model=model or os.getenv(f"{prefix}_MODEL", "deepseek-chat" if prefix == "DEEPSEEK" else "gpt-5")
        self.temperature=float(temperature if temperature is not None else os.getenv("LLM_TEMPERATURE", "1.0"))
        key=os.getenv(f"{prefix}_API_KEY")
        if not key: raise RuntimeError(f"{prefix}_API_KEY is not set")
        from openai import OpenAI
        kwargs={"api_key":key}
        if self.provider == "deepseek": kwargs["base_url"]="https://api.deepseek.com"
        kwargs.update({"timeout": 30.0, "max_retries": 1})
        self.client=OpenAI(**kwargs)

    def choose_action(self, task, state, actions):
        payload={"task":task["prompt"],"state":state.__dict__,"allowed_actions":actions}
        response=self.client.chat.completions.create(model=self.model, messages=[
            {"role":"system","content":"Choose exactly one allowed action for a data-analysis agent. Return JSON with keys action and rationale."},
            {"role":"user","content":json.dumps(payload, ensure_ascii=False)}], response_format={"type":"json_object"}, temperature=self.temperature)
        return parse_json_object(response.choices[0].message.content)


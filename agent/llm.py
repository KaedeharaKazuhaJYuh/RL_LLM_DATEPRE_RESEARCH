import json, os

class LLMClient:
    """OpenAI Responses API adapter. The key is read only from OPENAI_API_KEY."""
    def __init__(self, model=None):
        self.model=model or os.getenv("OPENAI_MODEL", "gpt-5")
        key=os.getenv("OPENAI_API_KEY")
        if not key: raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import OpenAI
        self.client=OpenAI(api_key=key)

    def choose_action(self, task, state, actions):
        payload={"task":task["prompt"],"state":state.__dict__,"allowed_actions":actions}
        response=self.client.responses.create(model=self.model, input=[
            {"role":"system","content":"Choose exactly one allowed action for a data-analysis agent. Return JSON with keys action and rationale."},
            {"role":"user","content":json.dumps(payload, ensure_ascii=False)}], store=False)
        return json.loads(response.output_text)


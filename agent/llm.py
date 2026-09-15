"""Optional DeepSeek-compatible policy; no API calls during local test matrices."""
import json,os,urllib.request
from agent.tools import DESCRIPTIONS
from agent.deepseek_config import settings, credential_present
class LLMClient:
    def __init__(self):
        config=settings()
        self.model=config.get('DEEPSEEK_MODEL','deepseek-chat')
        self.key=config.get('DEEPSEEK_API_KEY')
        if not credential_present():raise RuntimeError('DEEPSEEK_API_KEY is not configured; use process environment or ignored .env.local')
        self.temperature=float(config.get('LLM_TEMPERATURE','0'))
        self.last_usage={};self.last_response_id=None
    def choose(self,task,state,allowed):
        public={'prompt':task['prompt'],'parameters':task['params'],'state':state,'tools':{a:DESCRIPTIONS[a] for a in allowed}}
        body={'model':self.model,'temperature':self.temperature,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'Select exactly one allowed tool for the task. Return JSON with action and a short rationale. Parameters are supplied by the task. Never invent results.'},{'role':'user','content':json.dumps(public,ensure_ascii=False)}]}
        request=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(request,timeout=max(.1,min(30,task['constraints']['max_seconds']))) as response:data=json.load(response)
        self.last_usage=data.get('usage',{});self.last_response_id=data.get('id')
        choice=json.loads(data['choices'][0]['message']['content'])
        if not isinstance(choice,dict) or choice.get('action') not in allowed:raise ValueError('model returned invalid action')
        return choice

"""Optional DeepSeek-compatible policy; no API calls during local test matrices."""
import json,os,urllib.request
from agent.tools import DESCRIPTIONS
from agent.deepseek_config import settings, credential_present

def parse_step(content,allowed,fixed_bindings=False):
    text=content.strip();repaired=False
    if text.startswith('```') and text.endswith('```'):
        parts=text.splitlines()
        if parts[0] not in ('```','```json'):raise ValueError('unsupported fenced format')
        text='\n'.join(parts[1:-1]);repaired=True
    choice=json.loads(text)
    if not isinstance(choice,dict) or choice.get('action') not in list(allowed)+['stop']:
        raise ValueError('invalid step action')
    if fixed_bindings:choice={'action':choice['action']}
    elif choice['action']!='stop' and not isinstance(choice.get('params'),dict):
        raise ValueError('step parameters required')
    return choice,repaired

class LLMClient:
    def choose_step(self,task,state,allowed):
        self.last_usage={};self.last_response_id=None;self.last_format_repaired=False
        public={'prompt':task['prompt'],'request_parameters':task['params'],'state':state,
                'tools':{a:DESCRIPTIONS[a] for a in allowed}}
        body={'model':self.model,'temperature':self.temperature,'response_format':{'type':'json_object'},
              'messages':[{'role':'system','content':'Choose the next tool based on the request and execution history. Return JSON with action and params (a JSON object), or action stop when complete. Generate the tool parameters from the request and observed columns. Mutating tool outputs automatically become the next input. Failed calls do not change state. Do not repeat successful work. No results may be invented.'},
                          {'role':'user','content':json.dumps(public,ensure_ascii=False)}]}
        if task.get('fixed_bindings'):
            body['messages'][0]['content']='Choose the next tool from execution history and the user request. Return a JSON object with action only; stop is required when done. Tool parameters are fixed by state.parameter_bindings and applied automatically. Failed calls do not change the table. Do not repeat completed requirements or perform unrequested cleaning.'
        request=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(body).encode(),
                    headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
        self.last_usage=data.get('usage',{});self.last_response_id=data.get('id')
        choice,self.last_format_repaired=parse_step(data['choices'][0]['message']['content'],allowed,task.get('fixed_bindings',False))
        return choice

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

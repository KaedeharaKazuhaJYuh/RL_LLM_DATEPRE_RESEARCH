"""Read process settings or an ignored local DeepSeek env file without logging values."""
import os
from research.io import ROOT


def settings():
    values={}
    path=ROOT/'.env.local'
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            name,sep,value=line.partition('=')
            name=name.strip()
            if sep and name in ('DEEPSEEK_API_KEY','DEEPSEEK_MODEL','LLM_TEMPERATURE'):
                values[name]=value.strip().strip('"').strip("'")
    for name in ('DEEPSEEK_API_KEY','DEEPSEEK_MODEL','LLM_TEMPERATURE'):
        if os.getenv(name): values[name]=os.environ[name]
    return values


def credential_present():
    key=settings().get('DEEPSEEK_API_KEY','').strip()
    return bool(key and key not in ('replace_with_your_key','your_key','YOUR_API_KEY'))

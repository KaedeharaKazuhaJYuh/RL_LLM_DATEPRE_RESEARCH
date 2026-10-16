"""Separate represented actor scope from independently evidenced action origin."""
import copy
import json
from functools import lru_cache
from . import SEMANTICS_VERSION
from ..coherent395 import suite as old
from ..lineage375 import SEMANTICS_VERSION as LEGACY_VERSION
from ..lineage375.semantics import public_evidence
from ..multistep.suite import require, same

TOKENS = {'historical_agent_action':'pre_handoff_actor','current_model_action':'active_actor',
          'current_model_start_history_index':'actor_handoff_history_index',LEGACY_VERSION:SEMANTICS_VERSION}
GENERATION_CONTRACT = {
    'axis':'Generation origin is separate from represented actor scope and publication correctness.',
    'scripted_fixture':'Matched to the pinned controlled program-execution fixture in this repository; not external historical authentication.',
    'unknown':'No recognized pinned program origin evidence for this observation.',
    'model_api_tool_action':'Reserved. This adapter has no positive model-generated tool-action evidence; API fact answers do not establish that origin for history.'}


def rename(value,reverse=False):
    tokens = {v:k for k,v in TOKENS.items()} if reverse else TOKENS
    if isinstance(value,dict):
        pairs = [(rename(k,reverse),rename(v,reverse)) for k,v in value.items()]
        require(len({k for k,v in pairs})==len(pairs),'actor-schema key collision')
        return dict(pairs)
    if isinstance(value,list):return [rename(v,reverse) for v in value]
    if isinstance(value,str):
        for a,b in tokens.items():value = value.replace(a,b)
    return value


@lru_cache(maxsize=1)
def pinned_fixture():
    catalog = json.loads((old.REPO/'faultda_bench/protocols/acceptance_v36.json').read_text(encoding='utf-8'))
    name = old.OUTPUT.relative_to(old.REPO).as_posix(); expected = catalog['files'][name]
    require(old.sha(old.OUTPUT)==expected,'pinned program fixture bytes')
    source = json.loads(old.OUTPUT.read_text(encoding='utf-8'))
    return expected,{old.digest(r['public_observation']) for r in source['rows']}


def origin_evidence(obs):
    source_hash,observations = pinned_fixture(); fingerprint = old.digest(obs)
    known = fingerprint in observations
    return {'history_generation_origin':'scripted_fixture' if known else 'unknown',
            'source_file':old.OUTPUT.relative_to(old.REPO).as_posix() if known else None,
            'source_sha256':source_hash if known else None,'observation_sha256':fingerprint,
            'provider_authenticity_verified':False}


def encode(obs):
    require(obs.get('responsibility_contract',{}).get('semantics_version')==LEGACY_VERSION,'legacy input version')
    require(not {'generation_contract','generation_context'} & set(obs),'reserved migration fields')
    # Validate original public evidence before translating the versioned vocabulary.
    public_evidence(obs)
    mapped = rename(copy.deepcopy(obs))
    mapped['generation_contract'] = copy.deepcopy(GENERATION_CONTRACT)
    mapped['generation_context'] = origin_evidence(obs)
    return mapped


def decode(obs):
    require(obs.get('responsibility_contract',{}).get('semantics_version')==SEMANTICS_VERSION,'neutral actor version')
    require(obs.get('responsibility_context',{}).get('semantics_version')==SEMANTICS_VERSION,'neutral context version')
    require(obs.get('generation_contract')==GENERATION_CONTRACT,'generation contract')
    evidence = obs.get('generation_context'); require(isinstance(evidence,dict),'generation context')
    base = {k:copy.deepcopy(v) for k,v in obs.items() if k not in ('generation_contract','generation_context')}
    legacy = rename(base,True)
    require(same(evidence,origin_evidence(legacy)),'origin binding; names alone cannot claim model generation')
    public_evidence(legacy)
    return legacy


def evidence_view(obs):
    return rename(public_evidence(decode(obs)))

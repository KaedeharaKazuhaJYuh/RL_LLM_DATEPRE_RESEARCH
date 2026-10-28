"""Evaluate the frozen policies on the explicitly selected seen-development profiles."""
from faultda_bench.vericost565 import instances, policies


def evaluate_seen(regimes=None, *, workers=1):
    profiles = [row['profile_id'] for row in instances.load()['profiles']
                if row['kind'] == 'seen_development']
    if not profiles:
        raise ValueError('No seen-development profiles are available')
    return policies.evaluate_learned(model='rev1', workers=workers, instance_set='dev_seen',
                                     regimes=regimes, profiles=profiles)

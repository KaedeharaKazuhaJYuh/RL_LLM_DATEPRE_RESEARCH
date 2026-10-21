"""Public revision index; no numeric verification or action recommendation."""
def revision_index(obs):
    snapshot = None
    acknowledged = None
    last_inspect = -1
    events = []
    for i, h in enumerate(obs['history']):
        r = h['response']; action = h['action']
        revision = r.get('revision') if r.get('ok') is True else None
        if type(revision) is int and action in ('inspect', 'publish', 'status'):
            acknowledged = revision if acknowledged is None else max(acknowledged, revision)
            events.append({'history_index': i, 'action': action, 'revision': revision})
        if action == 'inspect' and type(revision) is int:
            snapshot = revision; last_inspect = i
    writes = [i for i,h in enumerate(obs['history']) if i > last_inspect and h['action']=='publish']
    return {'source': 'program_derived_public_history_index', 'last_inspect_history_index': last_inspect,
            'last_inspect_revision': snapshot, 'highest_acknowledged_revision': acknowledged,
            'snapshot_older_than_acknowledged_revision': snapshot is not None and acknowledged is not None and snapshot < acknowledged,
            'publish_attempt_indices_after_snapshot': writes, 'acknowledged_revision_events': events,
            'limits': 'An inspect report describes its snapshot only. Timeout does not certify failure or success. This index neither reconstructs current report contents nor verifies numbers, safety, or whether to stop. Full history is retained.'}

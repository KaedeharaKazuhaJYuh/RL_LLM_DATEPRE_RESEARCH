from ..semantic.environment import SemanticEnv

MODES = ('healthy', 'stage_only', 'shared_compute')


class ComputeFaultEnv(SemanticEnv):
    """Trusted fault injector; no fault mode is added to public observations."""
    def __init__(self, task, folder, *, mode, evidence, budget):
        if mode not in MODES:
            raise ValueError('unknown computation fault')
        self._mode = mode
        self._initializing = True
        super().__init__(task, folder, evidence=evidence, budget=budget,
                         commit_fault=False, semantic_fault=False)
        self._initializing = False

    def _compute(self, params):
        record = super()._compute(params)
        if self._mode == 'shared_compute' or (self._mode == 'stage_only' and not self._initializing):
            # Wrong numbers are materialized in the real staged file and ledger.
            # Parameters, input hashes, and storage integrity remain correct.
            record['output'] = {key: value + 1.0 for key, value in record['output'].items()}
        return record

"""Frozen selective recovery; calibration uses every calibration label."""
import re
from research.v3_recovery import FrozenRecoveryPolicy


def insufficient(message):
    return not message.strip() or bool(re.fullmatch(r"\s*\w*(?:Error|Exception)\s*:?\s*", message))


class SelectiveRecoveryPolicy(FrozenRecoveryPolicy):
    def calibrate(self, texts, labels):
        self.confidence_threshold = float('-inf')
        rows = [(self.confidence(t), super(SelectiveRecoveryPolicy, self).predict(t) == y)
                for t, y in zip(texts, labels) if not insufficient(t)]
        # Accept no calibration errors, maximizing empirical coverage. No test labels enter selection.
        candidates = sorted({c for c, _ in rows})
        self.confidence_threshold = float('inf')
        for threshold in candidates:
            accepted = [ok for c, ok in rows if c >= threshold]
            if accepted and all(accepted):
                self.confidence_threshold = threshold
                break
        return self

    def predict(self, text):
        if insufficient(text):
            return 'escalate'
        return super().predict(text)


def metrics(records):
    accepted = [r for r in records if r['prediction'] != 'escalate']
    correct = sum(r['classification_correct'] for r in accepted)
    executed = sum(r['execution_passed'] for r in accepted)
    return {'tasks': len(records), 'accepted': len(accepted), 'escalated': len(records)-len(accepted),
            'coverage': len(accepted)/len(records) if records else 0,
            'accepted_accuracy': correct/len(accepted) if accepted else None,
            'selective_risk': 1-correct/len(accepted) if accepted else None,
            'execution_passed': executed,
            'execution_rate': executed/len(records) if records else 0,
            'accepted_execution_failure_rate': 1-executed/len(accepted) if accepted else None}

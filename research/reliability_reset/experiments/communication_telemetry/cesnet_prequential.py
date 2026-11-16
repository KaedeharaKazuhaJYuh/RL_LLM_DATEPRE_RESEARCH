"""Weekly predict-seal-score-release orchestration for CESNET development experiments."""
from __future__ import annotations

import hashlib
import os
from datetime import date
from pathlib import Path
from typing import Callable

import numpy as np

from .cesnet_input import FlowBatch, iter_batches


def run_week(archive_path: Path, dates: list[str], predict: Callable[[FlowBatch], np.ndarray],
             classes: np.ndarray, budget: int, seed: int, prediction_path: Path,
             batch_size: int = 4096) -> tuple[dict, list[tuple[str, int, int]]]:
    """Seal all predictions before evaluation; release only a uniform label sample afterward.

    A returned label tuple is (date, table row index, APP code). The evaluator reads
    all labels for aggregate scoring, but the callback receives only unlabeled batches.
    The caller must keep the predictor and update phases separate; this API is not a
    security boundary against a callback that reads the archive independently.
    """
    classes = np.asarray(classes, dtype=np.int32)
    if classes.ndim != 1 or not len(classes) or len(np.unique(classes)) != len(classes):
        raise ValueError('classes must be a nonempty unique one-dimensional list')
    windows = {(day.isocalendar().year, day.isocalendar().week) for day in map(date.fromisoformat, dates)}
    if len(windows) != 1:
        raise ValueError('dates must all belong to one ISO year and week')
    if budget < 0 or prediction_path.exists():
        raise ValueError('budget must be nonnegative and prediction path must be new')
    predictions, row_ids, date_ids = [], [], []
    for batch in iter_batches(archive_path, dates, batch_size):
        predicted = np.asarray(predict(batch))
        if predicted.shape != (len(batch.row_indices),) or not np.issubdtype(predicted.dtype, np.integer):
            raise ValueError('predictor must return one integer class code per flow')
        if not np.isin(predicted, classes).all():
            raise ValueError('predictor returned class outside frozen vocabulary')
        predictions.append(predicted.astype(np.int32))
        row_ids.append(batch.row_indices)
        date_ids.extend(batch.dates)
    if not predictions:
        raise ValueError('no flows in specified dates')
    y_pred = np.concatenate(predictions)
    ids = np.concatenate(row_ids)
    if budget > len(ids):
        raise ValueError('label budget exceeds weekly population')
    dates_array = np.asarray(date_ids, dtype='U10')
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = prediction_path.with_name(prediction_path.name + '.tmp')
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, date=dates_array, row=ids, prediction=y_pred)
    os.replace(temporary, prediction_path)
    prediction_sha256 = hashlib.sha256(prediction_path.read_bytes()).hexdigest()

    # Evaluator has access to ground truth only after the prediction file is sealed.
    true_parts = []
    offset = 0
    for batch in iter_batches(archive_path, dates, batch_size, include_labels=True):
        size = len(batch.row_indices)
        if not np.array_equal(ids[offset:offset + size], batch.row_indices) or not np.array_equal(
            dates_array[offset:offset + size], np.asarray(batch.dates)
        ):
            raise ValueError('evaluation rows differ from sealed prediction order')
        true_parts.append(batch.labels)
        offset += size
    y_true = np.concatenate(true_parts)
    if len(y_true) != len(y_pred):
        raise ValueError('evaluation count differs from sealed predictions')
    f1 = []
    for code in classes:
        tp = int(np.count_nonzero((y_pred == code) & (y_true == code)))
        fp = int(np.count_nonzero((y_pred == code) & (y_true != code)))
        fn = int(np.count_nonzero((y_pred != code) & (y_true == code)))
        f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
    score = {'flows': len(y_true), 'accuracy': float(np.mean(y_pred == y_true)),
             'macro_f1_fixed_vocabulary': float(np.mean(f1)), 'vocabulary_size': len(classes),
             'out_of_vocabulary_truth': int(np.count_nonzero(~np.isin(y_true, classes))),
             'label_budget': budget, 'label_seed': seed, 'prediction_sha256': prediction_sha256}
    rng = np.random.default_rng(seed)
    selected = np.sort(rng.choice(len(y_true), size=budget, replace=False))
    released = [(str(dates_array[i]), int(ids[i]), int(y_true[i])) for i in selected]
    return score, released

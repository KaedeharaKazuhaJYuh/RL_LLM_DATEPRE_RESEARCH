"""Read completed CESNET flows using the frozen event and summary field contract."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator

import numpy as np
import tables

SUMMARY_FIELDS = (
    'BYTES', 'BYTES_REV', 'PACKETS', 'PACKETS_REV', 'DURATION',
    'PHIST_SRC_SIZES', 'PHIST_DST_SIZES', 'PHIST_SRC_IPT', 'PHIST_DST_IPT',
    'FLAG_CWR', 'FLAG_CWR_REV', 'FLAG_ECE', 'FLAG_ECE_REV',
    'FLAG_URG', 'FLAG_URG_REV', 'FLAG_ACK', 'FLAG_ACK_REV',
    'FLAG_PSH', 'FLAG_PSH_REV', 'FLAG_RST', 'FLAG_RST_REV',
    'FLAG_SYN', 'FLAG_SYN_REV', 'FLAG_FIN', 'FLAG_FIN_REV',
    'FLOW_ENDREASON_IDLE', 'FLOW_ENDREASON_ACTIVE', 'FLOW_ENDREASON_END', 'FLOW_ENDREASON_OTHER',
)


@dataclass(frozen=True)
class FlowBatch:
    events: np.ndarray  # [flow, packet, channel]; channel order IPT, DIR, SIZE, PUSH_FLAG
    mask: np.ndarray  # [flow, packet]
    summary: np.ndarray  # [flow, 57] in SUMMARY_FIELDS order, histograms flattened
    dates: tuple[str, ...]
    row_indices: np.ndarray  # table-local indices for reproducible sample selection
    labels: np.ndarray | None  # APP enum codes, visible only when explicitly requested


def iter_batches(archive_path: Path, dates: list[str], batch_size: int = 4096,
                 *, include_labels: bool = False) -> Iterator[FlowBatch]:
    """Read specified calendar dates in chronological order; no normalization or sampling."""
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    parsed = [date.fromisoformat(day) for day in dates]
    if len(set(parsed)) != len(parsed):
        raise ValueError('dates must not repeat')
    with tables.open_file(archive_path, mode='r') as archive:
        for day in sorted(parsed):
            table = archive.get_node('/flows/D' + day.strftime('%Y%m%d'))
            required = {'PPI', 'PPI_LEN', 'APP', *SUMMARY_FIELDS}
            missing = required.difference(table.colnames)
            if missing:
                raise ValueError(f'{day}: missing fields {sorted(missing)}')
            if table.coldtypes['PPI'].shape != (4, 30):
                raise ValueError(f'{day}: unexpected PPI shape')
            for start in range(0, table.nrows, batch_size):
                stop = min(start + batch_size, table.nrows)
                rows = table.read(start, stop)
                lengths = rows['PPI_LEN'].astype(np.int32)
                if np.any(lengths > 30):
                    raise ValueError(f'{day}: PPI_LEN exceeds stored sequence')
                mask = np.arange(30)[None, :] < lengths[:, None]
                events = rows['PPI'].transpose(0, 2, 1).copy()
                events[~mask] = 0
                summary = np.concatenate([
                    np.asarray(rows[field]).reshape(len(rows), -1).astype(np.float64)
                    for field in SUMMARY_FIELDS
                ], axis=1)
                labels = rows['APP'].astype(np.int32) if include_labels else None
                yield FlowBatch(events, mask, summary, (day.isoformat(),) * len(rows),
                                np.arange(start, stop, dtype=np.int64), labels)

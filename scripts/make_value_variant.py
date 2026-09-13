"""Restore historical CSVs; their old scoring remains historical."""
from research.benchmark import repair_legacy_values
if __name__=='__main__':
    repair_legacy_values();print('historical CSVs repaired; new research uses tasks/v2')

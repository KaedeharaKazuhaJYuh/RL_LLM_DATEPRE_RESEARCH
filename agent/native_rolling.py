"""Opt-in C++ rolling mean backend; no automatic fallback or oracle access."""
import ctypes
import os
from pathlib import Path


def rolling_mean(values, window):
    library_path = os.environ.get('V5_ROLLING_LIB')
    if not library_path:
        raise RuntimeError('V5_ROLLING_LIB is required for native rolling_mean')
    library = ctypes.CDLL(str(Path(library_path).resolve()))
    function = library.v5_rolling_mean
    function.argtypes = (ctypes.POINTER(ctypes.c_double), ctypes.c_size_t,
                         ctypes.c_size_t, ctypes.POINTER(ctypes.c_double), ctypes.c_size_t)
    function.restype = ctypes.c_int
    count = len(values)
    output_count = max(0, count - window + 1)
    input_array = (ctypes.c_double * count)(*values)
    output_array = (ctypes.c_double * output_count)()
    if function(input_array, count, window, output_array, output_count):
        raise ValueError('native rolling_mean rejected input')
    return list(output_array)

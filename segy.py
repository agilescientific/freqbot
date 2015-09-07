# -*- coding: utf-8 -*-
"""
Son of segypy: A Python module for writing 2D SEG-Y formatted data.

Thomas Mejer Hansen, 2005-2006
Pete Forman 2006
Andrew Squelch 2007
Agile Geoscience 2015 — write segy only
source: http://segymat.cvs.sourceforge.net/viewvc/segymat/SegyPY/segypy.py

TODO:
    Extend to 3D.
"""
import struct

import numpy as np

from utils import set_type
from utils import SH_def
from utils import STH_def


def _getDefaultSegyHeader(ntraces, ns, dt):
    """
    Set up the default filewide header.

    dt in seconds.
    """
    SH = {"Job": {"pos": 3200, "type": "int32", "def": 0}}

    for key in SH_def:
        SH[key] = SH_def[key].get('def') or 0

    SH["ntraces"] = ntraces
    SH["ns"] = ns
    SH["dt"] = int(dt * 1000000)
    SH["DataSampleFormat"] = 5  # IEEE
    SH["EnsembleFold"] = 1
    SH["TraceSorting"] = 4  # 2 = cdp, 4 = stack, default 0 = unknown
    SH["MeasurementSystem"] = 1  # m, default 0 = unknown, 2 = ft
    SH["NumberOfExtTextualHeaders"] = 0
    SH["FixedLengthTraceFlag"] = 1  # = constant
    SH["SegyFormatRevisionNumber"] = 1

    return SH


def _getDefaultSegyTraceHeaders(ntraces, ns, dt, t_min):
    """
    SH=getDefaultSegyTraceHeader()
    """
    STH = {"TraceSequenceLine": {"pos": 0, "type": "int32"}}

    for key in STH_def:
        STH[key] = np.zeros(ntraces, dtype=np.int32)

    for a in range(ntraces):
        STH["TraceSequenceLine"][a] = a + 1
        STH["TraceSequenceFile"][a] = a + 1
        STH["FieldRecord"][a] = 1000
        STH["TraceNumber"][a] = a + 1
        STH["ns"][a] = ns
        STH["dt"][a] = int(dt * 1000000)  # microseconds
        STH["DelayRecordingTime"][a] = int(t_min * 1000)  # milliseconds

    return STH


def _writeSegyStructure(fo, data, SH, STH):
    """
    internal method
    """
    revision = SH["SegyFormatRevisionNumber"]
    dsf = SH["DataSampleFormat"]
    if revision in [100, 256]:
        revision = 1

    # WRITE SEGY HEADER
    for key in SH_def:
        pos = SH_def[key]["pos"]
        fmt = SH_def[key]["type"]
        value = SH[key]

        _putValue(value, fo, pos, fmt)

    # WRITE SEGY TRACES
    ctype = SH_def['DataSampleFormat']['datatype'][revision][dsf]
    bps = SH_def['DataSampleFormat']['bps'][revision][dsf]

    sizeT = 240 + SH['ns']*bps

    for i, tr in enumerate(data):

        index = 3600 + i*sizeT

        # WRITE TRACE HEADER
        for key in STH_def:
            pos = index + STH_def[key]["pos"]
            fmt = STH_def[key]["type"]
            value = STH[key][i]
            _putValue(value, fo, pos, fmt)

        # WRITE DATA
        cformat = '>' + ctype  # Always big endian.
        for j, s in enumerate(tr):
            strVal = struct.pack(cformat, s)
            fo.seek(index + 240 + j*struct.calcsize(cformat))
            fo.write(strVal)

    fo.seek(0)

    return None


def _putValue(value, fo, index, ctype):
    """
    putValue
    """
    size, ctype = set_type(ctype)

    cformat = '>' + ctype

    strVal = struct.pack(cformat, value)
    fo.seek(index)
    fo.write(strVal)

    return None


def write_segy(data, fo, dt, t_min, STHin={}, SHin={}):
    """
    write_segy

    Times in seconds.

    """
    ns = data.shape[1]
    ntraces = data.shape[0]

    SH = _getDefaultSegyHeader(ntraces, ns, dt)
    STH = _getDefaultSegyTraceHeaders(ntraces, ns, dt, t_min)

    # ADD STHin, if exists...
    for key in STHin:
        for a in range(ntraces):
            STH[key] = STHin[key][a]

    # ADD SHin, if exists...
        for key in SHin:
            SH[key] = SHin[key]

    _writeSegyStructure(fo, data, SH, STH)

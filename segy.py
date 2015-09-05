# -*- coding: utf-8 -*-
"""
SEGY file writing.

"""
import numpy as np

import segpy


def write_segy(data, fo, dtype=5):
    print('entering write_segy()')
    sample_interval = 4  # ms

    if data.ndim == 3:
        # These are really indices, not line numbers.
        inlines = np.arange(0, data.shape[0], 1)
        xlines = np.arange(0, data.shape[1], 1)
    else:
        inlines = [0]
        xlines = np.arange(0, data.shape[0], 1)

    # dtype = 5  # {8: 'int8', 1: 'ibm', 2: 'int32', 3: 'int16', 5: 'float32'}
    segy_type = segpy.datatypes.DATA_SAMPLE_FORMAT_TO_SEG_Y_TYPE[dtype]

    # Using BytesIO so dispense with the file handling
    # with open(outfile, 'wb') as fo:

    # Write the text header. It can contain whatever you like.
    info_header = [
        "Created using segpy github.com/rob-smallshire/segpy",
    ]

    trh = [s[:80]+(80-len(s))*' ' for s in info_header]  # Exactly 80 cols
    trh = trh[:40]  # Limit to 40 lines
    segpy.toolkit.write_textual_reel_header(fo, trh, segpy.encoding.ASCII)  # No EBCDIC

    # Build the binary header.
    brh = segpy.binary_reel_header.BinaryReelHeader()
    # MANDATORY FIELDS
    # brh.data_traces_per_ensemble = 0 # Pre-stack data
    # brh.auxiliary_traces_per_ensemble = 0 # Pre-stack data
    brh.sample_interval = sample_interval*1000  # microseconds
    brh.num_samples = data.shape[-1]
    brh.fixed_length_trace_flag = 1  # Default is 0 = varying trace length
    # brh.format_revision_num = 1 # Default is 1
    brh.data_sample_format = dtype  # Default is 5 = IEEE float
    # brh.num_extended_textual_headers = 0 # Default is 0
    # RECOMMENDED FIELDS
    brh.ensemble_fold = 1  # Default = 0
    brh.trace_sorting = 4  # 2 = cdp, 4 = stack, default 0 = unknown
    brh.measurement_system = 1  # m, default 0 = unknown, 2 = ft

    # Write the binary header.
    segpy.toolkit.write_binary_reel_header(fo, brh)

    # Pre-format trace header format.
    t = segpy.trace_header.TraceHeaderRev1
    trace_header_packer = segpy.toolkit.make_header_packer(t)

    # Make a trace geometry.
    xxlines, iinlines = np.meshgrid(xlines, inlines)
    trace_iter = np.vstack([iinlines.flat, xxlines.flat]).T

    # Iterate over the geometry and populate the traces.
    i = 0
    for inline, xline in trace_iter:
        i += 1

        if data.ndim == 3:
            samples = data[inline, xline]
        else:
            samples = data[xline]

        trace_header = segpy.trace_header.TraceHeaderRev1()

        trace_header.field_record_num = i
        trace_header.trace_num = i
        trace_header.num_samples = len(samples)
        trace_header.sample_interval = sample_interval

        if data.ndim == 3:
            trace_header.file_sequence_num = inline
            trace_header.ensemble_num = xline
            trace_header.inline_number = inline
            trace_header.crossline_number = xline
        else:
            trace_header.file_sequence_num = 1000 + i
            trace_header.ensemble_num = xline
            trace_header.shotpoint_number = xline

        # Write trace header and data.
        segpy.toolkit.write_trace_header(fo, trace_header, trace_header_packer)
        segpy.toolkit.write_trace_samples(fo, samples, seg_y_type=segy_type)

    print('leaving write_segy()')

    return None

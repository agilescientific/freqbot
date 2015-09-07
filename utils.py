# -*- coding: utf-8 -*-
"""
Utils for ageobot.

"""
import datetime
import struct

import boto3


def get_url(databytes, uuid1):

    file_link = ''
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(minutes=240)
    success = False

    try:
        from secrets import KEY, SECRET
        session = boto3.session.Session(aws_access_key_id=KEY,
                                        aws_secret_access_key=SECRET,
                                        region_name='us-east-1'
                                        )
        client = session.client('s3')
        key = uuid1 + '.segy'
        bucket = 'ageobot'
        acl = 'public-read'  # For public file.
        params = {'Body': databytes,
                  'Expires': expires,
                  'Bucket': bucket,
                  'Key': key,
                  'ACL': acl,
                  }
        r = client.put_object(**params)
        success = r['ResponseMetadata']['HTTPStatusCode'] == 200
    except:
        print('Upload to S3 failed')

    print(str(success))

    if success:
        # Only do this if successfully uploaded, because
        # you always get a link, even if no file.
        if acl == 'public-read':
            file_link = 'https://s3.amazonaws.com/{}/{}'.format(bucket, key)
        else:
            try:
                params = {'Bucket': bucket,
                          'Key': key}
                file_link = client.generate_presigned_url('get_object',
                                                          Params=params,
                                                          ExpiresIn=3600)
            except:
                print('Retrieval of S3 link failed')

    return file_link


def build_params(method, avg,
                 t_min, t_max, dt_param,
                 region, tr_sp,
                 traces='',
                 url=''):
    """
    Build a dict of parameters, mostly those passed in.
    """
    params = {'method': method}
    params['avg'] = avg
    params['time_range'] = [t_min, t_max]
    params['dt'] = dt_param
    params['region'] = region
    params['trace_spacing'] = tr_sp
    if traces is not '':
        params['traces'] = traces.tolist()
    else:
        params['traces'] = ''
    params['url'] = url
    return params


def set_type(ctype):
    l_long = struct.calcsize('l')
    l_ulong = struct.calcsize('L')
    l_short = struct.calcsize('h')
    l_ushort = struct.calcsize('H')
    l_char = struct.calcsize('c')
    l_uchar = struct.calcsize('B')
    l_float = struct.calcsize('f')

    if (ctype == 'l') | (ctype == 'long') | (ctype == 'int32'):
        size = l_long
        ctype = 'l'
    elif (ctype == 'L') | (ctype == 'ulong') | (ctype == 'uint32'):
        size = l_ulong
        ctype = 'L'
    elif (ctype == 'h') | (ctype == 'short') | (ctype == 'int16'):
        size = l_short
        ctype = 'h'
    elif (ctype == 'H') | (ctype == 'ushort') | (ctype == 'uint16'):
        size = l_ushort
        ctype = 'H'
    elif (ctype == 'c') | (ctype == 'char'):
        size = l_char
        ctype = 'c'
    elif (ctype == 'B') | (ctype == 'uchar'):
        size = l_uchar
        ctype = 'B'
    elif (ctype == 'f') | (ctype == 'float'):
        size = l_float
        ctype = 'f'
    elif (ctype == 'ibm'):
        size = l_float
    else:
        size = None
        ctype = None

    return size, ctype


#  Initialize SEGY HEADER
SH_def = {"Job": {"pos": 3200, "type": "int32", "def": 0}}
SH_def["Line"] = {"pos": 3204, "type": "int32", "def": 0}
SH_def["Reel"] = {"pos": 3208, "type": "int32", "def": 0}
SH_def["DataTracePerEnsemble"] = {"pos": 3212, "type": "int16", "def": 0}
SH_def["AuxiliaryTracePerEnsemble"] = {"pos": 3214, "type": "int16", "def": 0}
SH_def["dt"] = {"pos": 3216, "type": "uint16", "def": 1000}
SH_def["dtOrig"] = {"pos": 3218, "type": "uint16", "def": 0}
SH_def["ns"] = {"pos": 3220, "type": "uint16", "def": 0}
SH_def["nsOrig"] = {"pos": 3222, "type": "uint16", "def": 0}
SH_def["DataSampleFormat"] = {"pos": 3224, "type": "int16", "def": 5}
SH_def["DataSampleFormat"]["descr"] = {0: {
    1: "IBM Float",
    2: "32 bit Integer",
    3: "16 bit Integer",
    8: "8 bit Integer"}}

SH_def["DataSampleFormat"]["descr"][1] = {
    1: "IBM Float",
    2: "32 bit Integer",
    3: "16 bit Integer",
    5: "IEEE",
    8: "8 bit Integer"}

SH_def["DataSampleFormat"]["bps"] = {0: {
    1: 4,
    2: 4,
    3: 2,
    8: 1}}
SH_def["DataSampleFormat"]["bps"][1] = {
    1: 4,
    2: 4,
    3: 2,
    5: 4,
    8: 1}
SH_def["DataSampleFormat"]["datatype"] = {0: {
    1: 'ibm',
    2: 'l',
    3: 'h',
    8: 'B'}}
SH_def["DataSampleFormat"]["datatype"][1] = {
    1: 'ibm',
    2: 'l',
    3: 'h',
    5: 'f',
    8: 'B'}

SH_def["EnsembleFold"] = {"pos": 3226, "type": "int16", "def":1}
SH_def["TraceSorting"] = {"pos": 3228, "type": "int16", "def":4}
SH_def["VerticalSumCode"] = {"pos": 3230, "type": "int16", "def":0}
SH_def["SweepFrequencyEnd"] = {"pos": 3234, "type": "int16", "def":0}
SH_def["SweepLength"] = {"pos": 3236, "type": "int16", "def":0}
SH_def["SweepType"] = {"pos": 3238, "type": "int16", "def":0}
SH_def["SweepChannel"] = {"pos": 3240, "type": "int16", "def":0}
SH_def["SweepTaperlengthStart"] = {"pos": 3242, "type": "int16", "def":0}
SH_def["SweepTaperLengthEnd"] = {"pos": 3244, "type": "int16", "def":0} 
SH_def["TaperType"] = {"pos": 3246, "type": "int16", "def":0}
SH_def["CorrelatedDataTraces"] = {"pos": 3248, "type": "int16", "def":0}
SH_def["BinaryGain"] = {"pos": 3250, "type": "int16", "def":0}
SH_def["AmplitudeRecoveryMethod"] = {"pos": 3252, "type": "int16", "def":0}
SH_def["MeasurementSystem"] = {"pos": 3254, "type": "int16", "def":1} 
SH_def["ImpulseSignalPolarity"] = {"pos": 3256, "type": "int16", "def":0}
SH_def["VibratoryPolarityCode"] = {"pos": 3258, "type": "int16", "def":0}
SH_def["Unassigned1"] = {"pos": 3260, "type": "int16",  "n":120, "def":0}
SH_def["SegyFormatRevisionNumber"] = {"pos": 3500, "type": "uint16", "def":1} # not 100
SH_def["FixedLengthTraceFlag"] = {"pos": 3502, "type": "uint16", "def":1} 
SH_def["NumberOfExtTextualHeaders"] = {"pos": 3504, "type": "uint16", "def":0}
SH_def["Unassigned2"] = {"pos": 3506, "type": "int16",  "n":47, "def":0} 


#  Initialize SEGY TRACE HEADER SPECIFICATION
STH_def = {"TraceSequenceLine": {"pos": 0,"type": "int32"}}
STH_def["TraceSequenceFile"] = {"pos": 4,"type": "int32"}
STH_def["FieldRecord"] = {"pos": 8, "type": "int32"}
STH_def["TraceNumber"] = {"pos": 12,"type": "int32"}
STH_def["EnergySourcePoint"] =  {"pos": 16,"type": "int32"} 
STH_def["cdp"] =  {"pos": 20,"type": "int32"}
STH_def["cdpTrace"] =  {"pos": 24,"type": "int32"}
STH_def["TraceIdenitifactionCode"] = {"pos":28 ,"type": "uint16"}
STH_def["TraceIdenitifactionCode"]["descr"] = {0:{
    1: "Seismic data", 
    2: "Dead", 
    3: "Dummy", 
    4: "Time Break", 
    5: "Uphole", 
    6: "Sweep", 
    7: "Timing", 
    8: "Water Break"}}
STH_def["TraceIdenitifactionCode"]["descr"][1] = {
    -1: "Other",
     0: "Unknown",
    1: "Seismic data",
    2: "Dead",
    3: "Dummy",
    4: "Time break",
    5: "Uphole",
    6: "Sweep",
    7: "Timing",
    8: "Waterbreak",
    9: "Near-field gun signature",
    10: "Far-field gun signature",
    11: "Seismic pressure sensor",
    12: "Multicomponent seismic sensor - Vertical component",
    13: "Multicomponent seismic sensor - Cross-line component",
    14: "Multicomponent seismic sensor - In-line component",
    15: "Rotated multicomponent seismic sensor - Vertical component",
    16: "Rotated multicomponent seismic sensor - Transverse component",
    17: "Rotated multicomponent seismic sensor - Radial component",
    18: "Vibrator reaction mass",
    19: "Vibrator baseplate",
    20: "Vibrator estimated ground force",
    21: "Vibrator reference",
    22: "Time-velocity pairs"}
STH_def["NSummedTraces"] = {"pos":30 ,"type": "int16"}
STH_def["NStackedTraces"] = {"pos":32 ,"type": "int16"} #'int16'); % 32
STH_def["DataUse"] = {"pos":34 ,"type": "int16"} #'int16'); % 34
STH_def["DataUse"]["descr"] = {0: {
    1: "Production", 
    2: "Test"}}
STH_def["DataUse"]["descr"][1] = STH_def["DataUse"]["descr"][0]
STH_def["offset"] = {"pos":36 ,"type": "int32"} #'int32');             %36
STH_def["ReceiverGroupElevation"] = {"pos":40 ,"type": "int32"} #'int32');             %40
STH_def["SourceSurfaceElevation"] = {"pos":44 ,"type": "int32"} #'int32');             %44
STH_def["SourceDepth"] = {"pos":48 ,"type": "int32"} #'int32');             %48
STH_def["ReceiverDatumElevation"] = {"pos":52 ,"type": "int32"} #'int32');             %52
STH_def["SourceDatumElevation"] = {"pos":56 ,"type": "int32"} #'int32');             %56
STH_def["SourceWaterDepth"] = {"pos":60 ,"type": "int32"} #'int32');  %60
STH_def["GroupWaterDepth"] = {"pos":64 ,"type": "int32"} #'int32');  %64
STH_def["ElevationScalar"] = {"pos":68 ,"type": "int16"} #'int16');  %68
STH_def["SourceGroupScalar"] = {"pos":70 ,"type": "int16"} #'int16');  %70
STH_def["SourceX"] = {"pos":72 ,"type": "int32"} #'int32');  %72
STH_def["SourceY"] = {"pos":76 ,"type": "int32"} #'int32');  %76
STH_def["GroupX"] = {"pos":80 ,"type": "int32"} #'int32');  %80
STH_def["GroupY"] = {"pos":84 ,"type": "int32"} #'int32');  %84
STH_def["CoordinateUnits"] = {"pos":88 ,"type": "int16"} #'int16');  %88
STH_def["CoordinateUnits"]["descr"] = {1: {
    1: "Length (meters or feet)",
    2: "Seconds of arc"}}
STH_def["CoordinateUnits"]["descr"][1] = {
    1: "Length (meters or feet)",
    2: "Seconds of arc",
    3: "Decimal degrees",
    4: "Degrees, minutes, seconds (DMS)"}   
STH_def["WeatheringVelocity"] = {"pos":90 ,"type": "int16"} #'int16');  %90
STH_def["SubWeatheringVelocity"] = {"pos":92 ,"type": "int16"} #'int16');  %92
STH_def["SourceUpholeTime"] = {"pos":94 ,"type": "int16"} #'int16');  %94
STH_def["GroupUpholeTime"] = {"pos":96 ,"type": "int16"} #'int16');  %96
STH_def["SourceStaticCorrection"] = {"pos":98 ,"type": "int16"} #'int16');  %98
STH_def["GroupStaticCorrection"] = {"pos":100 ,"type": "int16"} #'int16');  %100
STH_def["TotalStaticApplied"] = {"pos":102 ,"type": "int16"} #'int16');  %102
STH_def["LagTimeA"] = {"pos":104 ,"type": "int16"} #'int16');  %104
STH_def["LagTimeB"] = {"pos":106 ,"type": "int16"} #'int16');  %106
STH_def["DelayRecordingTime"] = {"pos":108 ,"type": "int16"} #'int16');  %108
STH_def["MuteTimeStart"] = {"pos":110 ,"type": "int16"} #'int16');  %110
STH_def["MuteTimeEND"] = {"pos":112 ,"type": "int16"} #'int16');  %112
STH_def["ns"] = {"pos":114 ,"type": "uint16"} #'uint16');  %114
STH_def["dt"] = {"pos":116 ,"type": "uint16"} #'uint16');  %116
STH_def["GainType"] = {"pos":119 ,"type": "int16"} #'int16');  %118
STH_def["GainType"]["descr"] = {0: {
    1: "Fixes", 
    2: "Binary",
    3: "Floating point"}}
STH_def["GainType"]["descr"][1] = STH_def["GainType"]["descr"][0]
STH_def["InstrumentGainConstant"] = {"pos":120 ,"type": "int16"} #'int16');  %120
STH_def["InstrumentInitialGain"] = {"pos":122 ,"type": "int16"} #'int16');  %%122
STH_def["Correlated"] = {"pos":124 ,"type": "int16"} #'int16');  %124
STH_def["Correlated"]["descr"] = {0: {
    1: "No", 
    2: "Yes"}}
STH_def["Correlated"]["descr"][1] = STH_def["Correlated"]["descr"][0]

STH_def["SweepFrequenceStart"] = {"pos":126 ,"type": "int16"} #'int16');  %126
STH_def["SweepFrequenceEnd"] = {"pos":128 ,"type": "int16"} #'int16');  %128
STH_def["SweepLength"] = {"pos":130 ,"type": "int16"} #'int16');  %130
STH_def["SweepType"] = {"pos":132 ,"type": "int16"} #'int16');  %132
STH_def["SweepType"]["descr"] = {0: {
    1: "linear", 
    2: "parabolic",
    3: "exponential",
    4: "other"}}
STH_def["SweepType"]["descr"][1] = STH_def["SweepType"]["descr"][0]

STH_def["SweepTraceTaperLengthStart"] = {"pos":134 ,"type": "int16"} #'int16');  %134
STH_def["SweepTraceTaperLengthEnd"] = {"pos":136 ,"type": "int16"} #'int16');  %136
STH_def["TaperType"] = {"pos":138 ,"type": "int16"} #'int16');  %138
STH_def["TaperType"]["descr"] = {0: {
    1: "linear", 
    2: "cos2c",
    3: "other"}}
STH_def["TaperType"]["descr"][1] = STH_def["TaperType"]["descr"][0]

STH_def["AliasFilterFrequency"] = {"pos":140 ,"type": "int16"} #'int16');  %140
STH_def["AliasFilterSlope"] = {"pos":142 ,"type": "int16"} #'int16');  %142
STH_def["NotchFilterFrequency"] = {"pos":144 ,"type": "int16"} #'int16');  %144
STH_def["NotchFilterSlope"] = {"pos":146 ,"type": "int16"} #'int16');  %146
STH_def["LowCutFrequency"] = {"pos":148 ,"type": "int16"} #'int16');  %148
STH_def["HighCutFrequency"] = {"pos":150 ,"type": "int16"} #'int16');  %150
STH_def["LowCutSlope"] = {"pos":152 ,"type": "int16"} #'int16');  %152
STH_def["HighCutSlope"] = {"pos":154 ,"type": "int16"} #'int16');  %154
STH_def["YearDataRecorded"] = {"pos":156 ,"type": "int16"} #'int16');  %156
STH_def["DayOfYear"] = {"pos":158 ,"type": "int16"} #'int16');  %158
STH_def["HourOfDay"] = {"pos":160 ,"type": "int16"} #'int16');  %160
STH_def["MinuteOfHour"] = {"pos":162 ,"type": "int16"} #'int16');  %162
STH_def["SecondOfMinute"] = {"pos":164 ,"type": "int16"} #'int16');  %164
STH_def["TimeBaseCode"] = {"pos":166 ,"type": "int16"} #'int16');  %166
STH_def["TimeBaseCode"]["descr"] = {0: {
    1: "Local", 
    2: "GMT", 
    3: "Other"}}
STH_def["TimeBaseCode"]["descr"][1] = {
    1: "Local", 
    2: "GMT", 
    3: "Other", 
    4: "UTC"}
STH_def["TraceWeightningFactor"] = {"pos":168 ,"type": "int16"} #'int16');  %170
STH_def["GeophoneGroupNumberRoll1"] = {"pos":170 ,"type": "int16"} #'int16');  %172
STH_def["GeophoneGroupNumberFirstTraceOrigField"] = {"pos":172 ,"type": "int16"} #'int16');  %174
STH_def["GeophoneGroupNumberLastTraceOrigField"] = {"pos":174 ,"type": "int16"} #'int16');  %176
STH_def["GapSize"] = {"pos":176 ,"type": "int16"} #'int16');  %178
STH_def["OverTravel"] = {"pos":178 ,"type": "int16"} #'int16');  %178
STH_def["OverTravel"]["descr"] = {0: {
    1: "down (or behind)", 
    2: "up (or ahead)",
    3: "other"}}
STH_def["OverTravel"]["descr"][1] = STH_def["OverTravel"]["descr"][0]


STH_def["cdpX"] = {"pos":180 ,"type": "int32"} #'int32');  %180
STH_def["cdpY"] = {"pos":184 ,"type": "int32"} #'int32');  %184
STH_def["Inline3D"] = {"pos":188 ,"type": "int32"} #'int32');  %188
STH_def["Crossline3D"] = {"pos":192 ,"type": "int32"} #'int32');  %192
STH_def["ShotPoint"] = {"pos":192 ,"type": "int32"} #'int32');  %196
STH_def["ShotPointScalar"] = {"pos":200 ,"type": "int16"} #'int16');  %200
STH_def["TraceValueMeasurementUnit"] = {"pos":202 ,"type": "int16"} #'int16');  %202
STH_def["TraceValueMeasurementUnit"]["descr"]  =  {1: {
    -1: "Other", 
    0: "Unknown (should be described in Data Sample Measurement Units Stanza) ", 
    1: "Pascal (Pa)", 
    2: "Volts (V)", 
    3: "Millivolts (v)", 
    4: "Amperes (A)", 
    5: "Meters (m)", 
    6: "Meters Per Second (m/s)", 
    7: "Meters Per Second squared (m/&s2)Other", 
    8: "Newton (N)", 
    9: "Watt (W)"}}
STH_def["TransductionConstantMantissa"] = {"pos":204 ,"type": "int32"} #'int32');  %204
STH_def["TransductionConstantPower"] = {"pos":208 ,"type": "int16"} #'int16'); %208
STH_def["TransductionUnit"] = {"pos":210 ,"type": "int16"} #'int16');  %210
STH_def["TransductionUnit"]["descr"]   =  STH_def["TraceValueMeasurementUnit"]["descr"] 
STH_def["TraceIdentifier"] = {"pos":212 ,"type": "int16"} #'int16');  %212
STH_def["ScalarTraceHeader"] = {"pos":214 ,"type": "int16"} #'int16');  %214
STH_def["SourceType"] = {"pos":216 ,"type": "int16"} #'int16');  %216
STH_def["SourceType"]["descr"]  =  {1: {
    -1: "Other (should be described in Source Type/Orientation stanza)",
     0: "Unknown",
     1: "Vibratory - Vertical orientation",
     2: "Vibratory - Cross-line orientation",
     3: "Vibratory - In-line orientation",
     4: "Impulsive - Vertical orientation",
     5: "Impulsive - Cross-line orientation",
     6: "Impulsive - In-line orientation",
     7: "Distributed Impulsive - Vertical orientation",
     8: "Distributed Impulsive - Cross-line orientation",
     9: "Distributed Impulsive - In-line orientation"}}

STH_def["SourceEnergyDirectionMantissa"] = {"pos":218 ,"type": "int32"} #'int32');  %218
STH_def["SourceEnergyDirectionExponent"] = {"pos":222 ,"type": "int16"} #'int16');  %222
STH_def["SourceMeasurementMantissa"] = {"pos":224 ,"type": "int32"} #'int32');  %224
STH_def["SourceMeasurementExponent"] = {"pos":228 ,"type": "int16"} #'int16');  %228
STH_def["SourceMeasurementUnit"] = {"pos":230 ,"type": "int16"} #'int16');  %230
STH_def["SourceMeasurementUnit"]["descr"]  =  {1: {
    -1: "Other (should be described in Source Measurement Unit stanza)",
    0: "Unknown",
    1: "Joule (J)",
    2: "Kilowatt (kW)",
    3: "Pascal (Pa)",
    4: "Bar (Bar)",
    4: "Bar-meter (Bar-m)",
    5: "Newton (N)",
    6: "Kilograms (kg)"}}
STH_def["UnassignedInt1"] = {"pos":232 ,"type": "int32"} #'int32');  %232
STH_def["UnassignedInt2"] = {"pos":236 ,"type": "int32"} #'int32');  %236


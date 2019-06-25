# -*- coding: utf-8 -*-
"""
Simple application to provide freq from images of seismic.
Freq code by endolith https://gist.github.com/endolith/255291
"""
from io import BytesIO
import uuid
import base64

from flask import Flask
from flask import make_response
from flask import request, jsonify, render_template

import urllib
import requests
import numpy as np
from PIL import Image

from bruges import get_bruges
import geophysics
from segy import write_segy
import utils
from errors import InvalidUsage

application = Flask(__name__)


@application.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


#
# Seismic frequency and SEGY bot
#
@application.route('/freq')
def freq():
    # Params from inputs.
    url = request.args.get('url')
    b64 = request.args.get('image')
    method = request.args.get('method') or 'xing'
    avg = request.args.get('avg') or 'mean'
    region = request.args.get('region')
    ntraces = request.args.get('ntraces') or '10'
    trace_spacing = request.args.get('trace_spacing') or 'regular'
    bins = request.args.get('bins') or '11'
    t_min = request.args.get('tmin') or '0'
    t_max = request.args.get('tmax') or '1'
    dt_param = request.args.get('dt') or 'auto'

    # Booleans.
    spectrum = request.args.get('spectrum') or 'false'
    segy = request.args.get('segy') or 'false'

    nope = {i: False for i in ('none', 'false', 'no', '0')}

    spectrum = nope.get(spectrum.lower(), True)
    segy = nope.get(segy.lower(), True)

    # Condition or generate params.
    ntraces = int(ntraces)
    bins = int(bins)
    t_min = float(t_min)
    t_max = float(t_max)
    uuid1 = str(uuid.uuid1())
    if region:
        region = [int(n) for n in region.split(',')]
    else:
        region = []

    # Fetch and crop image.
    if url:
        try:
            r = requests.get(url)
            im = Image.open(BytesIO(r.content))
        except Exception:
            payload = {'job_uuid': uuid1}
            payload['parameters'] = utils.build_params(method, avg,
                                                       t_min, t_max, dt_param,
                                                       region,
                                                       trace_spacing,
                                                       url=url)
            mess = 'Unable to open image from target URI.'
            raise InvalidUsage(mess, status_code=410, payload=payload)

    elif b64:
        try:
            im = Image.open(BytesIO(base64.b64decode(b64)))
        except Exception:
            payload = {'job_uuid': uuid1}
            payload['parameters'] = utils.build_params(method, avg,
                                                       t_min, t_max, dt_param,
                                                       region,
                                                       trace_spacing,
                                                       url=url)
            mess = 'Could not decode payload image. Check base64 encoding.'
            raise InvalidUsage(mess, status_code=410, payload=payload)
    else:
        payload = {'job_uuid': uuid1}
        payload['parameters'] = utils.build_params(method, avg,
                                                   t_min, t_max, dt_param,
                                                   region,
                                                   trace_spacing,
                                                   url=url)
        mess = 'You must provide an image.'
        raise InvalidUsage(mess, status_code=410, payload=payload)

    if region:
        try:
            im = im.crop(region)
        except Exception:
            mess = 'Improper crop parameters '
            raise InvalidUsage(mess, status_code=410)

    width, height = im.size[0], im.size[1]

    # Calculate dt and interpolate if necessary.
    if dt_param[:4].lower() == 'orig':
        dt = (t_max - t_min) / (height - 1)
    else:
        if dt_param[:4].lower() == 'auto':
            dts = [0.0005, 0.001, 0.002, 0.004, 0.008]
            for dt in sorted(dts, reverse=True):
                target = int(1 + (t_max - t_min) / dt)
                # Accept the first one that is larger than the current height.
                if target >= height:
                    break  # dt and target are set
        else:
            dt = float(dt_param)
            target = int((t_max - t_min) / dt)

        # If dt is not orig, we need to inpterpolate.
        im = im.resize((width, target), Image.ANTIALIAS)

    # Set up the image.
    grey = geophysics.is_greyscale(im)
    i = np.asarray(im) - 128
    i = i.astype(np.int8)
    if (not grey) and (i.ndim == 3):
        r, g, b = i[..., 0], i[..., 1], i[..., 2]
        i = np.sqrt(0.299 * r**2. + 0.587 * g**2. + 0.114 * b**2.)
    elif i.ndim == 3:
        i = i[..., 0]
    else:
        i = i

    # Get SEGY file link, if requested.
    if segy:
        try:
            databytes = BytesIO()
            write_segy(i, databytes, dt, t_min)
            databytes.seek(0)
        except:
            print('Write SEGY failed')
        else:
            file_link = utils.get_url(databytes, uuid1)

    # Do analysis.
    print("Starting analysis")
    m = {'auto': geophysics.freq_from_autocorr,
         'fft':  geophysics.freq_from_fft,
         'xing': geophysics.freq_from_crossings}
    traces = geophysics.get_trace_indices(i.shape[1], ntraces, trace_spacing)
    specs, f_list, p_list, snr_list, mis, mas = geophysics.analyse(i,
                                                                   t_min,
                                                                   t_max,
                                                                   traces,
                                                                   m[method])

    print("Finished analysis")

    # Compute statistics.
    print("***** f_list:", f_list)

    fsd, psd = np.nanstd(f_list), np.nanstd(p_list)
    fn, pn = len(f_list), len(p_list)

    if avg.lower() == 'trim' and fn > 4:
        f = geophysics.trim_mean(f_list, 0.2)
        if np.isnan(f):
            f = 0
    elif avg.lower() == 'mean' or (avg == 'trim' and fn <= 4):
        f = np.nanmean(f_list)
    else:
        mess = 'avg parameter must be trim or mean'
        raise InvalidUsage(mess, status_code=410)

    if avg.lower() == 'trim' and pn > 4:
        p = geophysics.trim_mean(p_list, 0.2)
    elif avg.lower() == 'mean' or (avg == 'trim' and pn <= 4):
        p = np.nanmean(p_list)
    else:
        mess = 'avg parameter must be trim or mean'
        raise InvalidUsage(mess, status_code=410)

    snrsd = np.nanstd(snr_list)
    snr = np.nanmean(snr_list)

    # Spectrum.
    print("Starting spectrum")

    try:
        spec = np.nanmean(np.dstack(specs), axis=-1)
        fs = i.shape[0] / (t_max - t_min)
        freq = np.fft.rfftfreq(i.shape[0], 1/fs)
        f_min = np.amin(mis)
        f_max = np.amax(mas)
    except:
        print("Failed spectrum")

        # Probably the image is not greyscale.
        payload = {'job_uuid': uuid1}
        payload['parameters'] = utils.build_params(method, avg,
                                                   t_min, t_max, dt_param,
                                                   region,
                                                   trace_spacing,
                                                   url=url)
        mess = 'Analysis error. Probably the colorbar is not greyscale.'
        raise InvalidUsage(mess, status_code=410, payload=payload)

    # Histogram.
    if bins:
        hist = np.histogram(i, bins=bins)
    else:
        hist = None

    # Construct the result and return.
    result = {'job_uuid': uuid1}

    result['status'] = 'success'
    result['message'] = ''
    result['result'] = {}
    result['result']['freq'] = {'peak': np.round(f, 2),
                                'sd': np.round(fsd, 2),
                                'n': fn,
                                'min': np.round(f_min, 2),
                                'max': np.round(f_max, 2)}
    result['result']['phase'] = {'avg': np.round(p, 2),
                                 'sd': np.round(psd, 2),
                                 'n': pn}
    result['result']['snr'] = {'avg': np.round(snr, 2),
                               'sd': np.round(snrsd, 2)}
    result['result']['greyscale'] = grey
    result['result']['dt'] = dt
    result['result']['img_size'] = {'original_height': height,
                                    'width': width,
                                    'resampled_height': target}

    if segy:
        result['result']['segy'] = file_link

    if spectrum:
        result['result']['spectrum'] = spec.tolist()
        result['result']['frequencies'] = freq.tolist()

    if hist:
        result['result']['histogram'] = {'counts': hist[0].tolist(),
                                         'bins':  hist[1].tolist()
                                         }

    result['parameters'] = utils.build_params(method, avg,
                                              t_min, t_max, dt_param,
                                              region,
                                              trace_spacing,
                                              url=url)

    return jsonify(result)

#
# Bruges logo and text generators
#
@application.route('/bruges')
@application.route('/bruges.png')
def bruges_png():

    p = float(request.args.get('p') or 0.5)
    n = int(request.args.get('n') or 1)
    style = str(request.args.get('style') or '')

    text = get_bruges(p, n)
    text = urllib.parse.quote_plus(text)

    base_url = "https://chart.googleapis.com/chart"

    if style.lower() == 'bubble':
        q = "?chst=d_bubble_text_small&chld=bb|{}|14AFCA|000000"
        query = q.format(text)
    else:
        q = "?chst=d_text_outline&chld=14AFCA|24|h|325396|b|{}"
        query = q.format(text)

    url = base_url + query

    r = requests.get(url)
    b = BytesIO(r.content)

    response = make_response(b.getvalue())
    response.mimetype = 'image/png'
    return response


@application.route('/bruges.json')
def bruges_json():

    p = float(request.args.get('p') or 0.5)
    n = int(request.args.get('n') or 1)

    text = get_bruges(p, n)
    dictionary = {'result': text,
                  'p': p,
                  'n': n,
                  }

    return jsonify(dictionary)


@application.route('/bruges.txt')
def bruges_text():

    p = float(request.args.get('p') or 0.5)
    n = int(request.args.get('n') or 1)

    text = get_bruges(p, n)
    return text


@application.route('/bruges.help')
def bruges_help():

    return render_template('bruges.html',
                           title='Bruges help')


@application.route('/')
def main():
    return render_template('index.html',
                           title='Home')


if __name__ == "__main__":
    application.debug = True
    application.run()

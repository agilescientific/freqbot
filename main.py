# -*- coding: utf-8 -*-
"""
Simple application to provide freq from images of seismic.
Freq code by endolith https://gist.github.com/endolith/255291

"""
from io import BytesIO
import uuid

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


@application.route('/freq')
def freq():

    # Params from inputs.
    url = request.args.get('url')
    method = request.args.get('method') or 'xing'
    avg = request.args.get('avg') or 'mean'
    region = request.args.get('region') or []
    ntraces = request.args.get('ntraces') or '10'
    trace_spacing = request.args.get('trace_spacing') or 'regular'
    bins = request.args.get('bins') or '9'
    t_min = request.args.get('tmin') or '0'
    t_max = request.args.get('tmax') or '1'
    t_max = request.args.get('tmax') or '1'

    # Booleans.
    spectrum = request.args.get('spectrum') or 'false'
    segy = request.args.get('segy') or 'false'

    nope = {i: False for i in ('none', 'false', 'no', '0')}

    spectrum = nope.get(spectrum.lower(), True)
    segy = nope.get(segy.lower(), True)

    # Condition or generate params.
    ntraces = int(ntraces)
    bins = float(bins)
    t_min = float(t_min)
    t_max = float(t_max)
    uuid1 = str(uuid.uuid1())

    # Fetch and crop image.
    try:
        r = requests.get(url)
        im = Image.open(BytesIO(r.content))
    except Exception:
        result = {'job_uuid': uuid.uuid1()}
        result['status'] = 'failed'
        m = 'Error. Unable to open image from target URI. '
        result['message'] = m
        result['parameters'] = utils.build_params(method, avg,
                                                  t_min, t_max,
                                                  region,
                                                  trace_spacing,
                                                  url=url)
        return jsonify(result)

    if region:
        r = [int(n) for n in region.split(',')]
        try:
            im = im.crop(r)
        except Exception:
            raise InvalidUsage('Improper crop parameters '+region, status_code=410)

    # Set up the image.
    grey = geophysics.is_greyscale(im)
    i = np.asarray(im) - 128
    i = i.astype(np.int8)
    if not grey:
        r, g, b = i[..., 0], i[..., 1], i[..., 2]
        i = np.sqrt(0.299 * r**2. + 0.587 * g**2. + 0.114 * b**2.)
    else:
        i = i[..., 0]

    # Get SEGY file link, if requested.
    if segy:
        try:
            databytes = BytesIO()
            write_segy(i, databytes)
            databytes.seek(0)
        except:
            print('Write SEGY failed')
        else:
            file_link = utils.get_url(databytes, uuid1)

    # Do analysis.
    m = {'auto': geophysics.freq_from_autocorr,
         'fft':  geophysics.freq_from_fft,
         'xing': geophysics.freq_from_crossings}
    traces = geophysics.get_trace_indices(i.shape[1], ntraces, trace_spacing)
    specs, f_list, p_list, snr_list, mis, mas = geophysics.analyse(i,
                                                                   t_min,
                                                                   t_max,
                                                                   traces,
                                                                   m[method])

    # Compute statistics.
    fsd, psd = np.nanstd(f_list), np.nanstd(p_list)
    fn, pn = len(f_list), len(p_list)

    if avg == 'trim' and fn > 4:
        f = geophysics.trim_mean(f_list, 0.2)
    elif avg == 'mean' or (avg == 'trim' and fn <= 4):
        f = np.nanmean(f_list)
    else:
        m = 'avg parameter must be trim or mean'
        raise InvalidUsage(m, status_code=410)

    if avg == 'trim' and pn > 4:
        p = geophysics.trim_mean(p_list, 0.2)
    elif avg == 'mean' or (avg == 'trim' and pn <= 4):
        p = np.nanmean(p_list)
    else:
        m = 'avg parameter must be trim or mean'
        raise InvalidUsage(m, status_code=410)

    snrsd = np.nanstd(snr_list)
    snr = np.nanmean(snr_list)

    # Spectrum.
    try:
        spec = np.mean(np.dstack(specs), axis=-1)
        fs = i.shape[0] / (t_max - t_min)
        freq = np.fft.rfftfreq(i.shape[0], 1/fs)
        f_min = np.amin(mis)
        f_max = np.amax(mas)
    except:
        # Probably the image is not greyscale.
        result = {'job_uuid': uuid.uuid1()}
        result['status'] = 'failed'
        m = 'Analysis error. Probably the colorbar is not greyscale.'
        result['message'] = m
        result['parameters'] = utils.build_params(method, avg,
                                                  t_min, t_max,
                                                  region,
                                                  trace_spacing,
                                                  url=url)

        return jsonify(result)

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
    result['result']['img_size'] = {'height': im.size[0], 'width': im.size[1]}

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
                                              t_min, t_max,
                                              region,
                                              trace_spacing,
                                              url=url)

    return jsonify(result)


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
    # application.debug = True
    application.run()

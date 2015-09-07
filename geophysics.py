# -*- coding: utf-8 -*-
"""
Geophysics for ageobot.

TODO: Move some of this to Bruges.

"""
import numpy as np
from PIL import ImageStat


def is_greyscale(im):
    stat = ImageStat.Stat(im)
    if sum(stat.sum[:3])/3 == stat.sum[0]:
        return True
    return False


def hilbert(s, phi=0):
    """
    Optional phase shift phi in degrees.

    I don't understand why I need to handle the
    real and complex parts separately.
    """
    n = s.size
    m = np.ceil((n + 1) / 2)

    r0 = np.exp(1j * np.radians(phi))

    # Real part.
    rr = np.ones(n, dtype=complex)
    rr[:m] = r0
    rr[m+1:] = np.conj(r0)

    # Imag part.
    ri = np.ones(n, dtype=complex)
    ri[:m] = r0
    ri[m+1:] = -1 * r0

    _Sr = rr * np.fft.fft(s)
    _Si = ri * np.fft.fft(s)

    hr = np.fft.ifft(_Sr)
    hi = np.fft.ifft(_Si)

    h = np.zeros_like(hr, dtype=complex)
    h += hr.real + hi.imag * 1j

    return h


def trim_mean(i, proportion):
    """
    Trim mean, roughly emulating scipy.stats.trim_mean().

    Must deal with arrays or lists.
    """
    a = np.array(i)
    n = a.size
    a = np.sort(a)
    k = int(np.floor(n*proportion))
    return np.mean(a[k:-k])


def parabolic(f, x):
    """
    Interpolation.
    """
    xv = 1/2. * (f[x-1] - f[x+1]) / (f[x-1] - 2 * f[x] + f[x+1]) + x
    yv = f[x] - 1/4. * (f[x-1] - f[x+1]) * (xv - x)
    return (xv, yv)


def freq_from_crossings(sig, fs):
    indices = ((sig[1:] >= 0) & (sig[:-1] < 0)).nonzero()
    crossings = [i - sig[i] / (sig[i+1] - sig[i]) for i in indices]
    return fs / np.mean(np.diff(crossings))


def freq_from_autocorr(sig, fs):
    sig = sig + 128
    corr = np.convolve(sig, sig[::-1], mode='full')
    corr = corr[len(corr)/2:]
    d = np.diff(corr)
    start = (d > 0).nonzero()[0][0]  # nonzero() returns a tuple
    peak = np.argmax(corr[start:]) + start
    px, py = parabolic(corr, peak)
    return fs / px


def get_spectrum(signal, fs):
    windowed = signal * np.blackman(len(signal))
    a = abs(np.fft.rfft(windowed))
    f = np.fft.rfftfreq(len(signal), 1/fs)

    db = 20 * np.log10(a)
    sig = db - np.amax(db) + 20
    indices = ((sig[1:] >= 0) & (sig[:-1] < 0)).nonzero()
    crossings = [z - sig[z] / (sig[z+1] - sig[z]) for z in indices]
    mi, ma = np.amin(crossings), np.amax(crossings)
    x = np.arange(0, len(f))  # for back-interpolation
    f_min = np.interp(mi, x, f)
    f_max = np.interp(ma, x, f)

    return f, a, f_min, f_max


def freq_from_fft(signal, fs):
    f, a, f_min, f_max = get_spectrum(signal, fs)
    i = np.argmax(a)
    true_i = parabolic(np.log(a), i)[0]
    return fs * true_i / len(signal)


def get_snr(i):
    """Bad algorithm
    """
    i += 128
    return np.nanmean(i) / np.nanstd(i)


def get_phase(i):
    e = hilbert(i)

    # Get the biggest 25 sample indices and sort them by amplitude
    biggest = np.argpartition(e.real, -25)[-25:]
    s = np.vstack((biggest, e.real[biggest])).T
    sort = s[s[:, 1].argsort()][::-1]

    # Prune the list down to the biggest for realz
    biggest_pruned = [sort[:, 0][0]]
    for ix in sort[:, 0][1:]:
        add = True
        for got in biggest_pruned:
            if abs(ix - got) < 5:  # made-up number
                add = False
        if add:
            biggest_pruned.append(ix)
            if len(biggest_pruned) == 5:
                break

    # Get the interpolated phase values
    results = []
    for ix in biggest_pruned:
        true_i = parabolic(np.log(abs(e)+0.01), ix)[0]
        x = np.arange(0, len(e))
        rad = np.interp(true_i, x, np.angle(e))
        results.append(np.degrees(rad))

    return np.nanmean(results)


def get_trace_indices(y, ntraces, spacing):
    if spacing == 'random':
        x = 0.05 + 0.9*np.random.random(ntraces)  # avoids edges
        ti = np.sort(x * y)
    else:
        n = ntraces + 1
        ti = np.arange(1./n, 1., 1./n) * y
    return np.round(ti).astype(int)


def analyse(i, t_min, t_max, trace_indices, func):
    fs = i.shape[0] / (t_max - t_min)

    spec, freq, phase, snr = [], [], [], []
    mis, mas = [], []
    for ti in trace_indices:
        trace = i[:, ti]
        try:
            f = func(trace, fs)
            freq.append(f)
            p = get_phase(trace)
            phase.append(p)
            snr.append(get_snr(trace))

            frq, amp, fmi, fma = get_spectrum(trace, fs)
            spec.append(amp)
            mis.append(fmi)
            mas.append(fma)
        except Exception:
            continue

    return spec, freq, phase, snr, mis, mas

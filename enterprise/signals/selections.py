# selections.py
"""Contains various selection functions to mask parameters by backend flags,
time-intervals, etc."""


import functools
import inspect

import numpy as np


def call_me_maybe(obj):
    """See `here`_ for description.

    .. _here: https://www.youtube.com/watch?v=fWNaR-rxAic
    """
    return obj() if hasattr(obj, "__call__") else obj


def selection_func(func):
    try:
        funcargs = inspect.getfullargspec(func).args
    except:
        funcargs = inspect.getargspec(func).args

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        targs = list(args)

        # check for mask
        mask = kwargs.get("mask", Ellipsis)
        if "mask" in kwargs:
            del kwargs["mask"]

        if len(targs) < len(funcargs) and "psr" in kwargs:
            psr = kwargs["psr"]

            for funcarg in funcargs[len(args) :]:
                if funcarg not in kwargs and hasattr(psr, funcarg):
                    attr = call_me_maybe(getattr(psr, funcarg))
                    if isinstance(attr, np.ndarray) and getattr(mask, "shape", [0])[0] == len(attr):
                        targs.append(attr[mask])
                    else:
                        targs.append(attr)

        if "psr" in kwargs and "psr" not in funcargs:
            del kwargs["psr"]

        return func(*targs, **kwargs)

    return wrapper


def Selection(func):
    """Class factory for TOA selection."""

    class Selection(object):
        def __init__(self, psr):
            self._psr = psr

        @property
        def masks(self):
            return selection_func(func)(psr=self._psr)

        def _get_masked_array_dict(self, masks, arr):
            return {key: val * arr for key, val in masks.items()}

        def __call__(self, parname, parameter, arr=None):
            params, kmasks = {}, {}
            for key, val in self.masks.items():
                kname = "_".join([key, parname]) if key else parname
                pname = "_".join([self._psr.name, kname])
                params.update({kname: parameter(pname)})
                kmasks.update({kname: val})

            if arr is not None:
                ma = self._get_masked_array_dict(kmasks, arr)
                ret = (params, ma)
            else:
                ret = params, kmasks
            return ret

    return Selection


# SELECTION FUNCTIONS


def cut_half(toas):
    """Selection function to split by data segment"""
    midpoint = (toas.max() + toas.min()) / 2
    return dict(zip(["t1", "t2"], [toas <= midpoint, toas > midpoint]))


def by_band(flags):
    """Selection function to split by PPTA frequency band under -B flag"""
    flagvals = np.unique(flags["B"])
    return {val: flags["B"] == val for val in flagvals}


def by_frontend(flags):
    """Selection function to split by frontend under -fe flag"""
    flagvals = np.unique(flags["fe"])
    return {val: flags["fe"] == val for val in flagvals}


def by_backend(backend_flags):
    """Selection function to split by backend flags."""
    flagvals = np.unique(backend_flags)
    return {val: backend_flags == val for val in flagvals}


def nanograv_backends(backend_flags):
    """Selection function to split by NANOGRav backend flags only."""
    flagvals = np.unique(backend_flags)
    ngb = ["ASP", "GASP", "GUPPI", "PUPPI", "YUPPI"]
    flagvals = [val for val in flagvals if any([b in val for b in ngb])]
    return {val: backend_flags == val for val in flagvals}


def by_telescope(telescope):
    """Selection function to split by telescope"""
    telescopes = np.unique(telescope)
    return {t: (telescope == t) for t in telescopes}


def no_selection(toas):
    """Default selection with no splitting."""
    return {"": np.ones_like(toas, dtype=bool)}


def custom_backends(cb):
    def backends(backend_flags):
        """Selection function to split by custom backend flags only.
        cb : list of str of the backends
        use None to recover by_backend
        use ["ASP", "GASP", "GUPPI", "PUPPI"] to recover nanograv_backends
        """
        nonlocal cb
        flagvals = np.unique(backend_flags)
        if cb is not None:
            cb = list(np.atleast_1d(cb))
            flagvals = [val for val in flagvals if any([b in val for b in cb])]
        else:
            pass
        return {val: backend_flags == val for val in flagvals}

    return backends


def custom_backends_dict(cb):
    def backends(backend_flags, flags, toas):
        """Selection function to split by custom flags dictionary only.
        cb : str, list or dict of flags and names
        use None to recover no_selection
        use {"B":None} to recover by_band
        use {"fe":None} to recover by_frontend
        use {"backend":None} to recover by_backend
        use {"backend":["ASP", "GASP", "GUPPI", "PUPPI"]} to recover nanograv_backends
        """
        nonlocal cb
        if isinstance(cb, str) or isinstance(cb, list):
            flagvals = np.unique(backend_flags)
            cb = list(np.atleast_1d(cb))
            flagvals = [val for val in flagvals if any([b in val for b in cb])]
            return {val: backend_flags == val for val in flagvals}
        elif isinstance(cb, dict):
            flagdict = {}
            for flagname in cb.keys():
                if flagname == "backend":
                    flagvals = np.unique(backend_flags)
                    if cb["backend"] is not None:
                        cb_key = list(np.atleast_1d(cb["backend"]))
                        flagvals = [val for val in flagvals if any([b in val for b in cb_key])]
                    else:
                        pass
                    flagdict.update({val: backend_flags == val for val in flagvals})
                else:
                    flagvals = np.unique(flags[flagname])
                    if cb[flagname] is not None:
                        cb_key = list(np.atleast_1d(cb[flagname]))
                        flagvals = [val for val in flagvals if any([b in val for b in cb_key])]
                    else:
                        pass
                    flagdict.update({val: flags[flagname] == val for val in flagvals})
            return flagdict
        else:
            return {"": np.ones_like(toas, dtype=bool)}

    return backends

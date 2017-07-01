#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read LDC's output format
"""

import os
from collections import defaultdict
import numpy as np
from tqdm import tqdm

def invert_dict(dct):
    """Inverts a dictionary from A -> B into one from B -> [A]"""
    ret = defaultdict(list)
    for k, v in dct.items():
        ret[v].append(k)
    return ret

def micro(S, C, T):
    """
    Computes micro-average over @elems
    """
    S, C, T = sum(S.values()), sum(C.values()), sum(T.values())
    P = C/S if S > 0. else 0.
    R = C/T if T > 0. else 0.
    F1 = 2 * P * R /(P + R) if C > 0. else 0.
    return P, R, F1

def macro(S, C, T):
    """
    Computes macro-average over @elems
    """
    P, R, F1 = 0., 0., 0.
    for i, s in enumerate(S):
        p = C[s]/S[s] if S[s] > 0. else 0.
        r = C[s]/T[s] if T[s] > 0. else 0.
        f1 = 2 * p * r /(p + r) if C[s] > 0. else 0.

        P  += (p  -  P)/(i+1)
        R  += (r  -  R)/(i+1)
        F1 += (f1 - F1)/(i+1)
    return P, R, F1

def bootstrap(xs, fn, samples=5000):
    """
    Return an array of statistics computed using a boostrap over xs
    """
    ys = []
    for xs_ in tqdm(np.random.choice(np.array(xs), (samples, len(xs)))):
        ys.append(fn(xs_))
    return np.array(ys)

def confidence_intervals(xs, fn, samples=5000, interval=0.95):
    """
    Compute confidence intervals for data.
    """
    ys = bootstrap(xs, fn, samples)

    mu = np.mean(ys, 0)
    lr = np.percentile(ys, [100*(1-interval)/2, 100*(interval + (1-interval)/2)], 0)
    return np.vstack((mu, lr))

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def stuple(span):
    return span.lower, span.upper

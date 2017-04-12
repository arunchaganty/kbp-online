#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A scoring script.
"""
import logging
from collections import defaultdict

import numpy as np

from .util import micro

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def k(entry):
    return (entry.ldc_id, entry.relation_provenances[0], entry.slot_value) # A cheap way to also correct for linking errors.

def kn(entry):
    return (entry.ldc_id, entry.slot_value) # A cheap way to also correct for linking errors.

def compute_entity_scores(gold, output, Q, mode="closed-world"):
    """
    @gold is a dictionary of {s: F*_s}.
    F*_s = {f: [m]}

    @pred is dictionary of {s: F_s}.
    F_s = {f: [m]}

    @returns (P, R, F1):
        P = {s: P_s}; P_s = F_s ^ F*_s / F_s
        R = {s: R_s}; R_s = F_s ^ F*_s / F*_s
        F1 = {s: F1_s}; F1_s = 2 P_s R_s / (P_s + R_s)
    """
    if mode == "closed-world" or mode == "condensed":
        key = k
    elif mode == "anydoc" or mode == "condensed-anydoc":
        key = kn
    else:
        raise ValueError("Unsupported mode: " + mode)

    G = defaultdict(lambda: defaultdict(set)) # Gold data
    Gr = {} # maps from entry to (s, f)
    for entry in gold:
        s = Q[entry.query_id] # Canonical query id.
        # NOTE: Considering inexact queries as correct because these are
        # considered correct as per recall computations.
        f = entry.eq # if (entry.slot_value_label == "C") else 0

        # If this is the first time this (subject, provenance)  pair has
        # been seen, then place it in Gr
        if (s, key(entry)) not in Gr:
            G[s][f].add(key(entry)) # Make a key out of this entry.
            Gr[s, key(entry)] = f
        # Else, resolve conflicting labels.
        else:
            # Remove any conflicting entries in 0 because of inexactness.
            f_ = Gr[s, key(entry)]
            if f == f_: continue # Nothing to worry about!
            elif f  > f_: # replace
                #logger.warning("conflicting labels for %s, %s; replacing %s with %s (%s)", s, key(entry), f, f_, G[s][f_])
                G[s][f_].remove(key(entry))
                G[s][f].add(key(entry))
                Gr[s, key(entry)] = f
            else:
                #logger.warning("conflicting labels for %s, %s; not replacing %s with %s (%s)", s, key(entry), f, f_, G[s][f_])
                pass # do nothing. Do not pass go, do not collect 1 million dollars.

    O = defaultdict(lambda: defaultdict(set)) # Gold data
    for entry in output:
        s = Q[entry.query_id]
        # If we are doing condensed lists, then do not add anything to
        # the output that isn't part of the evaluation data.
        if mode.startswith("condensed") and (s, key(entry)) not in Gr: continue

        f = Gr.get((s, key(entry)), 0)
        O[s][f].add(key(entry))

    S, C, T = {}, {}, {} # submitted, correct, total
    for s, Fs in G.items():
        Fs_ = O[s]

        # In the KBP evaluation, we know that only one mention has been
        # returned per purported entity -- thus, if mentions > 1 =>
        # there are duplicate mentions
        S[s] = sum(len(ms) for f, ms in Fs_.items()) #
        # S[s] = sum(1. if f > 0 else len(ms) for f, ms in Fs_.items())
        # What we'd use otherwise.
        C[s] = sum(1. for f in Fs if f > 0 and f in Fs_)
        T[s] = sum(1. for f in Fs if f > 0)

    return S, C, T

def compute_mention_scores(gold, output, key=k):
    """
    @gold is a dictionary of {s: F*_s}.
    F*_s = {f: [m]}

    @pred is dictionary of {s: F_s}.
    F_s = {f: [m]}

    @returns (P, R, F1):
        P = {s: P_s}; P_s = F_s ^ F*_s / F_s
        R = {s: R_s}; R_s = F_s ^ F*_s / F*_s
        F1 = {s: F1_s}; F1_s = 2 P_s R_s / (P_s + R_s)
    """
    G = defaultdict(set) # Gold data
    for entry in gold:
        if entry.eq > 0: # it's correct!
            G[entry.relation_provenances[0].doc_id].add(key(entry))

    O = defaultdict(set) # output data
    for entry in output:
        O[entry.relation_provenances[0].doc_id].add(key(entry))

    S, C, T = {}, {}, {} # submitted, correct, total
    for d, Fd in G.items():
        Fd_ = O[d]

        S[d] = len(Fd_)
        C[d] = len(Fd.intersection(Fd_))
        T[d] = len(Fd)

    return S, C, T

def compute_score_matrix(scores, E):
    X_rs = np.zeros((len(scores), len(E)))
    for i, runid in enumerate(sorted(scores)):
        S, C, T = scores[runid]
        for j, s in enumerate(sorted(S)):
            X_rs[i, j] = micro({s: S[s]}, {s: C[s]}, {s: T[s]})[-1]
    return X_rs

def measure_variance(X_st):
    """
    Measure the variance in the scores of X_rs
    """
    S, T = X_st.shape
    mu = X_st.mean()
    v_s = X_st.mean(1) - mu # average over columns
    v_t = X_st.mean(0) - mu # average over rows
    v_st = X_st - np.tile(v_s.reshape(S,1), (1, T)) - np.tile(v_t.reshape(1,T), (S, 1)) - mu

    s_s = v_s.var()
    s_t = v_t.var()
    s_st = v_st.var()

    assert abs(X_st.var() - (s_s + s_t + s_st)) < 1e-5

    phi = s_s/(s_s + s_t + s_st)
    rho = s_s/(s_s + s_st)

    return X_st.var(), s_s, s_t, s_st, phi, rho

def report_score_matrix(X_st, out, S, T):
    out.write("\t".join(["s", "s_s", "s_t", "s_st", "phi", "rho"]) + "\n")
    out.write("\t".join(map(str, measure_variance(X_st))) + "\n")

    # Actually print X_st

    out.write("\t" + "\t".join(sorted(T)) + "\n")
    for s, X_s in zip(sorted(S), X_st):
        out.write(s + "\t" + "\t".join(map("{:.4f}".format, X_s)) + "\n")

def standardize_scores(X_st):
    """
    Do a bias, variance correction on the t dimension
    """
    S = X_st.std(0)

    if abs(sum(X_st.mean(0)[S==0.])) > 1e-5:
        logger.warning("X_st matrix had some topic rows with identical scores")

    S[S == 0] = 1. #
    return ((X_st - X_st.mean(0))/S).mean(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to evaluate the system.
"""

import logging
from collections import Counter

import numpy as np

from . import counter_utils

logger = logging.getLogger(__name__)

class MixtureCounter(object):
    """
    Presents the mixture of a set of counters.
    Is readonly
    """

    def __init__(self, W, P):
        assert len(W) == len(P)
        self.m = len(P)
        self.W = W
        self.P = P
        self._keys = set()
        for i in range(self.m):
            self._keys.update(P[i].keys())

    def keys(self):
        return self._keys

    def __iter__(self):
        return iter(self._keys)

    def __getitem__(self, x):
        return sum(self.W[i] * self.P[i][x] for i in range(self.m))

# Simplest possible estimation procedures that assume access to the
# distribution (P) or (U).
def weighted_precision(P, Xs):
    """
    Compute precision without the complex weighting strategy.
    """
    m = len(Xs)
    pis = []
    for i in range(m):
        pi_i = 0.
        for x, fx in Xs[i]:
            pi_i += P[i][x] * fx
        pis.append(pi_i)
    return pis

def weighted_recall(U, P, Y):
    """
    Compute precision without the complex weighting strategy.
    """
    m = len(P)
    rhos = []
    Z = sum(U[x] for x, _ in Y)
    for i in range(m):
        rho_i = 0.
        for x, fx in Y:
            assert fx == 1.
            gxi = 1.0 if x in P[i] and P[i][x] > 0 else 0.
            rho_i += U[x] * gxi
        rhos.append(rho_i/Z)
    return rhos

def weighted_score(U, P, Y0, Xs):
    ps = weighted_precision(P, Xs)
    rs = weighted_recall(U, P, Y0)
    f1s = [2 * p * r / (p + r) if p + r > 0. else 0. for p, r in zip(ps, rs)]
    return ps, rs, f1s

# Simple sampling based estimators
def simple_precision(Xhs):
    """
    Compute precision without the complex weighting strategy.
    """
    m = len(Xhs)
    pis = []
    for i in range(m):
        pi_i = 0.
        for n_i, (_, fx) in enumerate(Xhs[i]):
            pi_i += (fx - pi_i)/(n_i+1)
        pis.append(pi_i)
    return pis

def simple_recall(U, P, Y0):
    m = len(P)

    Z = 0.
    for n, (x, fx) in enumerate(Y0):
        assert fx == 1.
        Z += (U[x] - Z)/(n+1)

    rhos = []
    for i in range(m):
        rho_i = 0.
        for n, (x, fx) in enumerate(Y0):
            assert fx == 1.
            gxi = 1.0 if x in P[i] and P[i][x] > 0 else 0.
            rho_i += (U[x]*gxi - rho_i)/(n+1)
        rhos.append(rho_i / Z)
    return rhos

def simple_score(U, P, Y0, Xhs):
    ps = simple_precision(Xhs)
    rs = simple_recall(U, P, Y0)
    f1s = [2 * p * r / (p + r) if p + r > 0. else 0. for p, r in zip(ps, rs)]
    return ps, rs, f1s

# Weight matrix computation
def compute_weights(P, Xhs, method="heuristic"):
    r"""
    Computes
    $w_{ij} \propto n_j \sum_{x} p_i(x) p_j(x)$
    """
    m = len(P)
    Ns = np.array([len(Xhs[i]) for i in range(m)])

    if method == "uniform":
        W = np.ones((m,m)) / m
    elif method == "heuristic":
        W = np.zeros((m,m))

        _P = [set(P[i]) for i in range(m)]
        for i in range(m):
            for j in range(i, m):
                W[i,j] = sum(P[i][x] * P[j][x] for x in _P[i].intersection(_P[j]))
                W[j,i] = W[i,j]
        W = W * Ns
        W = (W.T/W.sum(1)).T
    elif method == "size":
        W = np.zeros((m,m))
        for i in range(m):
            for j in range(m):
                W[i,j] = Ns[j]
        W = (W.T/W.sum(1)).T
    else:
        raise ValueError("Invalid weighting distribution")
    return W

def test_compute_weights_uniform():
    P = [
        {'a': 1.0, 'b': 0.0, 'c': 0.0},
        {'a': 0.0, 'b': 1.0, 'c': 0.0},
        {'a': 0.0, 'b': 0.0, 'c': 1.0},
        ]
    Xhs = [
        [('a',0.) for _ in range(10)],
        [('b',0.) for _ in range(50)],
        [('c',0.) for _ in range(100)],
        ]
    W = compute_weights(P, Xhs, "uniform")
    assert np.allclose(W, np.ones((3,3))/3)

def test_compute_weights_disjoint():
    P = [
        {'a': 1.0, 'b': 0.0, 'c': 0.0},
        {'a': 0.0, 'b': 1.0, 'c': 0.0},
        {'a': 0.0, 'b': 0.0, 'c': 1.0},
        ]
    Xhs = [
        [('a',0.) for _ in range(10)],
        [('b',0.) for _ in range(50)],
        [('c',0.) for _ in range(100)],
        ]
    W = compute_weights(P, Xhs, "heuristic")
    assert np.allclose(W, np.eye(3))

def test_compute_weights_identical():
    P = [
        {'a': 0.3, 'b': 0.2, 'c': 0.5},
        {'a': 0.3, 'b': 0.2, 'c': 0.5},
        {'a': 0.3, 'b': 0.2, 'c': 0.5},
        ]
    Xhs = [
        [('a',0.) for _ in range(10)],
        [('b',0.) for _ in range(50)],
        [('c',0.) for _ in range(100)],
        ]
    W = compute_weights(P, Xhs, "heuristic")
    assert np.allclose(W, np.array([
        [10./160., 50./160., 100./160.],
        [10./160., 50./160., 100./160.],
        [10./160., 50./160., 100./160.],
        ]))

# Proposal distribution generator
def construct_proposal_distribution(W, P):
    r"""
    Returns $q_i(x) = \sum_{j=1}^{m} w_{ij} p_{j}(x)$ and
    """
    m = len(P)

    Q = [Counter() for i in range(m)]
    for i in range(m):
        for x, v in P[i].items():
            for j in range(m):
                Q[j][x] += W[j][i] * v
    return Q

def test_construct_proposal_distribution():
    P = [
        {'a': 1.0, 'b': 0.0, 'c': 0.0},
        {'a': 0.0, 'b': 1.0, 'c': 0.0},
        {'a': 0.0, 'b': 0.0, 'c': 1.0},
        ]
    W = np.array([
        [0, 1., 0],
        [0.5, 0.3, 0.2],
        [0.2, 0.5, 0.2],
        ])
    Q = np.array([
        {'a': 0.0, 'b': 1.0, 'c': 0.0},
        {'a': 0.5, 'b': 0.3, 'c': 0.2},
        {'a': 0.2, 'b': 0.5, 'c': 0.2},
        ])
    Q_ = construct_proposal_distribution(W, P)
    for q, q_ in zip(Q, Q_):
        assert counter_utils.equals(q, q_)

def joint_precision(P, Xhs, W=None, Q=None, method="heuristic"):
    r"""
    Compute precision for a collection of samples, where
        P = [Counter], each element of P is a distribution over instances in $\sX$.
        Xs = [[x]], a list of samples drawn from each distribution.
    Returns:
    $\pi_i = \sum_{j=1}^{m} w_{ij}/n_j \sum_{x \in \Xh_j} p_i(x)/q_i(x) f(x)$, where
        $q_i(x) = \sum_{j=1}^{m} w_{ij} p_{j}(x)$ and
        $w_{ij} \propto n_j \sum_{x} p_i(x) p_j(x)$
    """
    m = len(P)

    if W is None:
        W = compute_weights(P, method)
    if Q is None:
        Q = construct_proposal_distribution(W, P)

    pis = []
    for i in range(m):
        pi_i = 0.

        for j in range(m):
            if W[i][j] == 0.: continue # just ignore this set.
            pi_ij = 0.
            for n_j, (x, fx) in enumerate(Xhs[j]):
                pi_ij += (P[i][x]/Q[i][x]*fx - pi_ij)/(n_j+1)
            pi_i += W[i][j] * pi_ij
        pis.append(pi_i)
    return pis

def pooled_recall(U, P, Xhs, W=None, Q=None, method="heuristic"):
    r"""
    \nu_i =
        \sum_{j} w_{j} \sum_{x \in Y_j} u(x)/q(x) g_i(x)/
        (\sum_{j} w_{j} \sum_{x \in Y_j} u(x)/q(x))
    w_j \propto n_j?
    """
    m = len(P)
    if W is None:
        W = compute_weights(P, method)
    if Q is None:
        Q = construct_proposal_distribution(W, P)

    nus = []
    for i in range(m):
        nu_i, Z_i = 0., 0.

        for j in range(m):
            if W[i][j] == 0.: continue # just ignore this set.
            nu_ij, Z_ij = 0., 0.
            for n_j, (x, fx) in enumerate(Xhs[j]):
                gx = 1.0 if fx > 0. else 0.0
                gxi = 1.0 if x in P[i] and fx > 0. else 0.0

                nu_ij += (U[x]/Q[i][x]*gxi - nu_ij)/(n_j+1)
                Z_ij += (U[x]/Q[i][x]*gx - Z_ij)/(n_j+1)
            nu_i += W[i][j] * nu_ij
            Z_i += W[i][j] * Z_ij
        nu_i = nu_i / Z_i if Z_i > 0 else 0
        nus.append(nu_i)
    return nus

def pool_recall(U, P, Y0):
    r"""
    Estimates the recall of the pool:
    \thetah = \frac{1}{Y0} \sum_{x \in Y_0} U(x) I[x \in X]
    """
    m = len(P)

    Z = 0.
    for n, (x, fx) in enumerate(Y0):
        assert fx == 1.
        Z += (U[x] - Z)/(n+1)

    theta = 0.
    for n, (x, fx) in enumerate(Y0):
        assert fx == 1.0
        gx = 1.0 if any(x in P[i] and P[i][x] > 0. for i in range(m)) else 0.
        theta += (U[x]*gx - theta)/(n+1)
    return theta/Z

def joint_recall(U, P, Y0, Xhs, W=None, Q=None):
    theta = pool_recall(U, P, Y0)
    nus = pooled_recall(U, P, Xhs, W=W, Q=Q)
    rhos = [theta * nu_i for nu_i in nus]
    return rhos

def joint_score(U, P, Y0, Xhs, W=None, Q=None):
    ps = joint_precision(P, Xhs, W=W, Q=Q)
    rs = joint_recall(U, P, Y0, Xhs, W=W, Q=Q)
    f1s = [2 * p * r / (p + r) if p + r > 0. else 0. for p, r in zip(ps, rs)]
    return ps, rs, f1s

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

def compute_weights(P, Xs, method="heuristic"):
    r"""
    Computes
    $w_{ij} \propto n_j \sum_{x} p_i(x) p_j(x)$
    """
    m = len(P)

    if method == "uniform":
        W = np.ones((m,m)) / m
    elif method == "heuristic":
        W = np.zeros((m,m))
        for i in range(m):
            for j in range(m):
                W[i,j] = sum(len(Xs[j]) * P[i][x] * P[j][x] for x in P[i])
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
    Xs = [
        [('a',0.) for _ in range(10)],
        [('b',0.) for _ in range(50)],
        [('c',0.) for _ in range(100)],
        ]
    W = compute_weights(P, Xs, "uniform")
    assert np.allclose(W, np.ones((3,3))/3)

def test_compute_weights_disjoint():
    P = [
        {'a': 1.0, 'b': 0.0, 'c': 0.0},
        {'a': 0.0, 'b': 1.0, 'c': 0.0},
        {'a': 0.0, 'b': 0.0, 'c': 1.0},
        ]
    Xs = [
        [('a',0.) for _ in range(10)],
        [('b',0.) for _ in range(50)],
        [('c',0.) for _ in range(100)],
        ]
    W = compute_weights(P, Xs, "heuristic")
    assert np.allclose(W, np.eye(3))

def test_compute_weights_identical():
    P = [
        {'a': 0.3, 'b': 0.2, 'c': 0.5},
        {'a': 0.3, 'b': 0.2, 'c': 0.5},
        {'a': 0.3, 'b': 0.2, 'c': 0.5},
        ]
    Xs = [ # these samples don't really matter.
        [('a',0.) for _ in range(10)],
        [('b',0.) for _ in range(50)],
        [('c',0.) for _ in range(100)],
        ]
    W = compute_weights(P, Xs, "heuristic")
    assert np.allclose(W, np.array([
        [10./160., 50./160., 100./160.],
        [10./160., 50./160., 100./160.],
        [10./160., 50./160., 100./160.],
        ]))

def construct_proposal_distribution(W, P):
    r"""
    Returns $q_i(x) = \sum_{j=1}^{m} w_{ij} p_{j}(x)$ and
    """
    m = len(P)

    Q = []
    for i in range(m):
        q = Counter()
        for j in range(m):
            q.update(counter_utils.scale(P[j], W[i][j]))
        Q.append(q)
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

def simple_precision(P, Xs):
    """
    Compute precision without the complex weighting strategy.
    """
    m = len(P)
    pis = []
    for i in range(m):
        pi_i = 0.
        for n_i, (_, fx) in enumerate(Xs[i]):
            pi_i += (fx - pi_i)/(n_i+1)
        pis.append(pi_i)
    return pis

def pooled_precision(P, Xs, method="heuristic"):
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

    W = compute_weights(P, Xs, method)
    Q = construct_proposal_distribution(W, P)

    pis = []
    for i in range(m):
        pi_i = 0.

        for j in range(m):
            if W[i][j] == 0.: continue # just ignore this set.
            pi_ij = 0.
            for n_j, (x, fx) in enumerate(Xs[j]):
                pi_ij += (P[i][x]/Q[i][x]*fx - pi_ij)/(n_j+1)
            pi_i += W[i][j] * pi_ij
        pis.append(pi_i)
    return pis

def pooled_recall(U, P, Xs):
    r"""
    \nu_i =
        \sum_{j} w_{j} \sum_{x \in Y_j} u(x)/q(x) g_i(x)/
        (\sum_{j} w_{j} \sum_{x \in Y_j} u(x)/q(x))
    w_j \propto n_j?

TODO: support u(x).
    """
    m = len(P)
    W = compute_weights(P, Xs, "uniform")
    Q = construct_proposal_distribution(W, P)

    nus = []
    for i in range(m):
        nu_i, Z_i = 0., 0.

        for j in range(m):
            if W[i][j] == 0.: continue # just ignore this set.
            nu_ij, Z_ij = 0., 0.
            for n_j, (x, fx) in enumerate(Xs[j]):
                nu_ij += (U[x]/Q[i][x]*fx - nu_ij)/(n_j+1)
                Z_ij += (U[x]/Q[i][x]*fx - Z_ij)/(n_j+1)
            nu_i += (nu_ij - nu_i)/(j+1)
            Z_i += (Z_ij - Z_i)/(j+1)
        nu_i = nu_i / Z_i if Z_i > 0 else 0
        nus.append(nu_i/Z_i)

    return nus

# TODO: write a test for pooled_recall_

def pool_recall(U, Y0, X):
    r"""
    Estimates the recall of the pool:
    \thetah = \frac{1}{Y0} \sum_{x \in Y_0} U(x) I[x \in X]
    """
    theta = 0.
    for n, x in enumerate(Y0):
        gx = 1.0 if any(x in Xi for Xi in X) else 0.0
        theta += (U[x]*gx - theta)/(n+1)
    return theta

def simple_recall(U, P, X, Y0):
    m = len(P)

    rhos = []
    for i in range(m):
        rho_i = 0
        for n, (x, fx) in enumerate(Y0):
            assert fx == 1.0
            gxi = 1.0 if x in P[i] and P[i][x] > 0 else 0.
            rho_i += (U[x]*gxi - rho_i)/(n+1)
        rhos.append(rho_i)
    return rhos

def recall(U, P, X, Y0, Xs):
    theta = pool_recall(U, Y0, X)
    nus = pooled_recall(U, P, Xs)
    rhos = [theta * nu_i for nu_i in nus]
    return rhos
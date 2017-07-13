#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to evaluate the system.
"""

import logging
from collections import Counter

import numpy as np
from tqdm import trange

from . import counter_utils
from .sample_util import sample_uniformly_with_replacement
from .schema import Score

logger = logging.getLogger(__name__)

def _avg(it, fn):
    ret, n = 0., 0.
    for x, fx in it:
        if fx is not None:
            ret += (fn(x, fx) -  ret)/(n+1)
            n += 1
    return ret

def _avg2(it, fn):
    ret, n = [0., 0.], 0.
    for x, fx in it:
        if fx is not None:
            ret_ = fn(x, fx)
            ret[0] += (ret_[0] -  ret[0])/(n+1)
            ret[1] += (ret_[1] -  ret[1])/(n+1)
            n += 1
    return ret

def _sum(it, fn):
    ret = 0.
    for x, fx in it:
        if fx is not None:
            ret += fn(x, fx)
    return ret

def _sum2(it, fn):
    ret = [0., 0.]
    for x, fx in it:
        if fx is not None:
            ret_ = fn(x, fx)
            ret[0] += ret_[0]
            ret[1] += ret_[1]
    return ret

# Simplest possible estimation procedures that assume access to the
# distribution (P) or (P0).
def weighted_precision(P, Xs):
    """
    Compute precision without the complex weighting strategy.
    """
    m = len(Xs)
    pis = []
    for i in range(m):
        pi_i = _sum(Xs[i], lambda x, fx:  P[i][x] * fx)
        pis.append(pi_i)
    return pis

def weighted_recall(P0, P, Y):
    """
    Compute precision without the complex weighting strategy.
    """
    m = len(P)
    rhos = []
    Z = sum(P0[x] for x, _ in Y)
    for i in range(m):
        rho_i = 0.
        for x, fx in Y:
            assert fx == 1.
            gxi = 1.0 if x in P[i] and P[i][x] > 0 else 0.
            rho_i += P0[x] * gxi
        rhos.append(rho_i/Z)
    return rhos

def weighted_score(P0, P, Y0, Xs):
    ps = weighted_precision(P, Xs)
    rs = weighted_recall(P0, P, Y0)
    f1s = [2 * p * r / (p + r) if p + r > 0. else 0. for p, r in zip(ps, rs)]
    return ps, rs, f1s

# Simple sampling based estimators
def simple_precision(Xhs):
    """
    Compute precision without the complex weighting strategy.

    @Xhs - a list of m lists of samples of [x, f(x)] drawn from some distribution; one for every system.
    @returns: a list of m precisions
    """
    m = len(Xhs)
    pis = []
    for i in range(m):
        pi_i = _avg(Xhs[i], lambda _, fx: fx)
        pis.append(pi_i)
    return pis

def simple_recall(P0, Y0):
    """
    @P0 - an unnormalized distribution Counter over all possible instances.
    @P - a list of M counters, giving p_i distributions for each system.
    @Y0 - a list of m lists, with [x, g(x)] samples over Y; one for each system.
    @returns: a list of m recalls
    """
    assert len(Y0) > 0

    rhos = []
    for Y0i in Y0:
        rho_i = 0.
        Z = 0.
        n = 0.
        for x, gxi in Y0i:
            if gxi is not None:
                rho_i += (P0[x]*gxi - rho_i)/(n+1)
                Z += (P0[x] - Z)/(n+1)
                n += 1
        rhos.append(rho_i / Z)
    return rhos

def simple_score(P0, P, Y0, Xhs):
    ps = simple_precision(Xhs)
    rs = simple_recall(P0, Y0)
    f1s = [2 * p * r / (p + r) if p + r > 0. else 0. for p, r in zip(ps, rs)]
    return ps, rs, f1s

def simple_score_with_intervals(P0, Ps, Y0, Xhs, num_epochs=100, interval=90):
    data = [[] for _ in Ps]

    logger.info("Computing base metrics")
    ps, rs, f1s = simple_score(P0, Ps, Y0, Xhs)
    for i, row in enumerate(zip(ps, rs, f1s)):
        data[i].append(row)

    logger.info("Bootstrapping")
    GX = [{x: gx for x, gx in Y} for Y in Y0]
    for _ in range(num_epochs):
        # Create a bootstrap sample of Y0_X by getting a new batch of X
        Y0_ = [x for x, _ in sample_uniformly_with_replacement(Y0[0], len(Y0[0]))]
        Y0_ = [[(x, GX[i][x]) for x in Y0_] for i, Y in enumerate(Y0)]
        Xhs_ = [sample_uniformly_with_replacement(X, len(X)) for X in Xhs]
        ps, rs, f1s = simple_score(P0, Ps, Y0_, Xhs_)
        for i, row in enumerate(zip(ps, rs, f1s)):
            data[i].append(row)
    ret = []
    for dat in data:
        dat = np.array(dat)
        p, r, f1 = dat[0]
        p_l, r_l, f1_l = np.percentile(dat[1:], 100-interval, 0)
        p_r, r_r, f1_r = np.percentile(dat[1:], interval, 0)

        ret.append(Score(
            p, r, f1,
            p_l, r_l, f1_l,
            p_r, r_r, f1_r,))
    return ret

# Weight matrix computation
def compute_weights(P, Xhs, method="heuristic"):
    r"""
    Computes
    $w_{ij} \propto n_j \sum_{x} p_i(x) p_j(x)$
    """
    m = len(P)
    Ns = np.array([sum(1 for _, fx in Xhs[i] if fx is not None) for i in range(m)])

    if method == "uniform":
        W = np.ones((m,m))
    elif method == "heuristic":
        W = np.zeros((m,m))

        _P = [set(P[i]) for i in range(m)]
        for i in range(m):
            for j in range(i, m):
                W[i,j] = sum(P[i][x] * P[j][x] for x in _P[i].intersection(_P[j]))
                W[j,i] = W[i,j]
        W = W * Ns
    elif method == "size":
        W = np.zeros((m,m))
        for i in range(m):
            for j in range(m):
                W[i,j] = Ns[j]
    else:
        raise ValueError("Invalid weighting distribution")

    Z = W.sum(1)
    W = (W.T/Z).T
    assert np.allclose(W.sum(1), np.ones(m))
    return W, Z

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
    W, Z = compute_weights(P, Xhs, "uniform")
    assert np.allclose(W, np.ones((3,3))/3)

    assert np.allclose((W.T * Z).T, np.ones((3,3)))

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
    W, _ = compute_weights(P, Xhs, "heuristic")
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
    W, Z = compute_weights(P, Xhs, "heuristic")
    assert np.allclose(W, np.array([
        [10./160., 50./160., 100./160.],
        [10./160., 50./160., 100./160.],
        [10./160., 50./160., 100./160.],
        ]))

    assert np.allclose((W.T * Z).T, np.array([
        [3.8, 19., 38.],
        [3.8, 19., 38.],
        [3.8, 19., 38.],
        ]))

def update_weights(Ps, Xhs, W, Z, method="heuristic"):
    """
    Updates the weights of W using the newly added P and Xhs.
    """
    assert method == "heuristic"
    assert len(Ps) == len(W) + 1
    m = len(W)
    if m == 0:
        return np.array([[1.]]), np.array([1.])

    # Copy over W
    W_ = np.zeros((m+1, m+1))
    # Undo normalization transform
    W_[:m,:m] = (W.T * Z).T

    Ns = np.array([sum(1 for _, fx in Xhs[i] if fx is not None) for i in range(m+1)])
    _P = [set(Ps[i]) for i in range(m+1)]

    i = m
    for j in range(m+1):
        w = sum(Ps[i][x] * Ps[j][x] for x in _P[i].intersection(_P[j]))
        W_[i,j] = Ns[j] * w
        W_[j,i] = Ns[i] * w

    Z = W_.sum(1)
    W_ = (W_.T/Z).T
    assert np.allclose(W_.sum(1), np.ones(m+1))
    return W_, Z

def test_update_weights():
    cases = [(
        [
            {'a': 1.0, 'b': 0.0, 'c': 0.0},
            {'a': 0.0, 'b': 1.0, 'c': 0.0},
            {'a': 0.0, 'b': 0.0, 'c': 1.0},
        ],[
            [('a',0.) for _ in range(10)],
            [('b',0.) for _ in range(50)],
            [('c',0.) for _ in range(100)],
        ]),([
            {'a': 0.3, 'b': 0.2, 'c': 0.5},
            {'a': 0.3, 'b': 0.2, 'c': 0.5},
            {'a': 0.3, 'b': 0.2, 'c': 0.5},
        ],[
            [('a',0.) for _ in range(10)],
            [('b',0.) for _ in range(50)],
            [('c',0.) for _ in range(100)],
        ]),([
            {'a': 0.3, 'b': 0.5, 'c': 0.2},
            {'a': 0.2, 'b': 0.2, 'c': 0.6},
            {'a': 0.1, 'b': 0.6, 'c': 0.3},
        ],[
            [('a',0.) for _ in range(10)],
            [('b',0.) for _ in range(50)],
            [('c',0.) for _ in range(100)],
        ]),]

    for P, Xhs in cases:
        W, Z = compute_weights(P[:1], Xhs[:1], "heuristic")
        for i in range(2,4):
            P_, Xhs_ = P[:i], Xhs[:i]
            W_, Z_ = update_weights(P_, Xhs_, W, Z, "heuristic")

            W, Z = compute_weights(P_, Xhs_, "heuristic")

            assert np.allclose(W, W_)
            assert np.allclose(Z, Z_)

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
        assert counter_utils.fequals(q, q_)

def update_proposal_distribution(W, Z, P, Q_, Z_):
    """
    Updates a proposal distribution using
    old proposal Q_ and Z_,
    new weights W and Z
    and P
    """
    m = len(Q_)
    assert len(W) == m + 1
    assert len(Z) == m + 1
    assert len(P) == m + 1
    assert len(Z_) == m

    Q = Q_[:] + [Counter(),]
    # Update old elements
    for i in range(m):
        # Scale up every element of Q and add a new bit for m.
        for x, v in Q[i].items():
            Q[i][x] = v * Z_[i]/Z[i]

        # Insert P[<m] for Q[m]
        for x, v in P[i].items():
            Q[m][x] += W[m][i] * v

    # And now add elements from P[m] everywhere
    for x, v in P[m].items():
        for j in range(m+1):
            Q[j][x] += W[j][m] * v

    return Q

def test_update_proposal_distribution():
    cases = [(
        [
            {'a': 1.0, 'b': 0.0, 'c': 0.0},
            {'a': 0.0, 'b': 1.0, 'c': 0.0},
            {'a': 0.0, 'b': 0.0, 'c': 1.0},
        ],[
            [('a',0.) for _ in range(10)],
            [('b',0.) for _ in range(50)],
            [('c',0.) for _ in range(100)],
        ]),([
            {'a': 0.3, 'b': 0.2, 'c': 0.5},
            {'a': 0.3, 'b': 0.2, 'c': 0.5},
            {'a': 0.3, 'b': 0.2, 'c': 0.5},
        ],[
            [('a',0.) for _ in range(10)],
            [('b',0.) for _ in range(50)],
            [('c',0.) for _ in range(100)],
        ]),([
            {'a': 0.3, 'b': 0.5, 'c': 0.2},
            {'a': 0.2, 'b': 0.2, 'c': 0.6},
            {'a': 0.1, 'b': 0.6, 'c': 0.3},
        ],[
            [('a',0.) for _ in range(10)],
            [('b',0.) for _ in range(50)],
            [('c',0.) for _ in range(100)],
        ]),]

    for P, Xhs in cases:
        W_, Z_ = compute_weights(P[:1], Xhs[:1], "heuristic")
        Q_ = construct_proposal_distribution(W_, P[:1])
        for i in range(2,4):
            P_, Xhs_ = P[:i], Xhs[:i]
            W, Z = update_weights(P_, Xhs_, W_, Z_, "heuristic")
            Q_ = update_proposal_distribution(W, Z, P_, Q_, Z_)
            Q = construct_proposal_distribution(W, P_)

            for q, q_ in zip(Q, Q_):
                assert counter_utils.fequals(q, q_)
            W_, Z_, Q_ = W, Z, Q


def joint_precision(P, Xhs, W=None, Q=None, method="heuristic"):
    r"""
    Compute precision for a collection of samples, where
        P = [Counter], each element of P is a distribution over instances in $\sX$.
        Xs = [[x, f(x)]], a list of samples drawn from each distribution.
    Returns:
    $\pi_i = \sum_{j=1}^{m} w_{ij}/n_j \sum_{x \in \Xh_j} p_i(x)/q_i(x) f(x)$, where
        $q_i(x) = \sum_{j=1}^{m} w_{ij} p_{j}(x)$ and
        $w_{ij} \propto n_j \sum_{x} p_i(x) p_j(x)$
    """
    m = len(P)

    if W is None:
        W, _ = compute_weights(P, Xhs, method)
    if Q is None:
        Q = construct_proposal_distribution(W, P)

    pis = []
    for i in range(m):
        pi_i = 0.

        for j in range(m):
            if W[i][j] == 0.: continue # just ignore this set.
            pi_ij = 0.
            n_j = 0
            for x, fx in Xhs[j]:
                if fx is not None:
                    pi_ij += (P[i][x]/Q[i][x]*fx - pi_ij)/(n_j+1)
                    n_j += 1
            pi_i += W[i][j] * pi_ij
        pis.append(pi_i)
    return pis

def pooled_recall(P0, P, Xhs, W=None, Q=None, method="heuristic"):
    r"""
    \nu_i =
        \sum_{j} w_{j} \sum_{x \in Y_j} u(x)/q(x) g_i(x)/
        (\sum_{j} w_{j} \sum_{x \in Y_j} u(x)/q(x))
    w_j \propto n_j?
    """
    m = len(P)
    if W is None:
        W, _ = compute_weights(P, Xhs, method)
    if Q is None:
        Q = construct_proposal_distribution(W, P)

    nus = []
    for i in range(m):
        nu_i, Z_i = 0., 0.

        for j in range(m):
            if W[i][j] == 0.: continue # just ignore this set.
            nu_ij, Z_ij = 0., 0.
            n_j = 0.
            for x, fx in Xhs[j]:
                if fx is not None:
                    gx = 1.0 if fx > 0. else 0.0
                    gxi = 1.0 if x in P[i] and fx > 0. else 0.0

                    nu_ij += (P0[x]/Q[i][x]*gxi - nu_ij)/(n_j+1)
                    Z_ij += (P0[x]/Q[i][x]*gx - Z_ij)/(n_j+1)
                    n_j += 1 
            nu_i += W[i][j] * nu_ij
            Z_i += W[i][j] * Z_ij
        nu_i = nu_i / Z_i if Z_i > 0 else 0
        nus.append(nu_i)
    return nus

def _merge_Y0(Y0):
    assert len(Y0) > 0
    assert len(Y0[0]) > 0

    ret = []

    m = len(Y0)
    n = len(Y0[0])
    for i in range(n):
        x = Y0[0][i][0]
        # handles the null case by defaulting to 0; this is ok because
        # gx = 0 only if NONE of the systems got this element.
        gx = max(Y0[j][i][1] or 0 for j in range(m))
        ret.append((x, gx))
    return ret

def test_merge_Y0():
    Y0 = [
        [('a', 0), ('b', 0), ('c', 1)],
        [('a', 1), ('b', 0), ('c', 0)],
        [('a', 0), ('b', 0), ('c', 0)],
        [('a', 1), ('b', 0), ('c', 0)],
        ]
    Y0_ = [('a', 1), ('b', 0), ('c', 1)]
    assert _merge_Y0(Y0) == Y0_

def pool_recall(P0, Y0):
    r"""
    @Y0 - a list of m lists, with [x, g(x)] samples over Y; one for each system.
    Estimates the recall of the pool:
    \thetah = \frac{1}{Y0} \sum_{x \in Y_0} P0(x) I[x \in X]
    """
    # A "merged" Y0 which combines gxi from each system.
    Y0_ = _merge_Y0(Y0)

    Z = 0.
    theta = 0.
    n = 0.
    for x, gx in Y0_:
        if gx is not None:
            theta += (P0[x]*gx - theta)/(n+1)
            Z += (P0[x] - Z)/(n+1)
            n += 1

    return theta/Z

def joint_recall(P0, P, Y0, Xhs, W=None, Q=None):
    theta = pool_recall(P0, Y0)
    nus = pooled_recall(P0, P, Xhs, W=W, Q=Q)
    rhos = [theta * nu_i for nu_i in nus]
    return rhos

def joint_score(P0, P, Y0, Xhs, W=None, Q=None):
    ps = joint_precision(P, Xhs, W=W, Q=Q)
    rs = joint_recall(P0, P, Y0, Xhs, W=W, Q=Q)
    f1s = [2 * p * r / (p + r) if p + r > 0. else 0. for p, r in zip(ps, rs)]
    return ps, rs, f1s

def joint_score_with_intervals(P0, Ps, Y0, Xhs, W=None, Q=None, num_epochs=100, interval=90):
    data = [[] for _ in Ps]

    logger.info("Precomputing weights")
    if W is None:
        W, _ = compute_weights(Ps, Xhs, "heuristic")
    if Q is None:
        Q = construct_proposal_distribution(W, Ps)

    logger.info("Computing base metrics")
    ps, rs, f1s = joint_score(P0, Ps, Y0, Xhs, W=W, Q=Q)
    for i, row in enumerate(zip(ps, rs, f1s)):
        data[i].append(row)

    logger.info("Bootstrapping")
    GX = [{x: gx for x, gx in Y} for Y in Y0]
    for _ in range(num_epochs):
        # Create a bootstrap sample of Y0_X by getting a new batch of X
        Y0_ = [x for x, _ in sample_uniformly_with_replacement(Y0[0], len(Y0[0]))]
        Y0_ = [[(x, GX[i][x]) for x in Y0_] for i, Y in enumerate(Y0)]
        Xhs_ = [sample_uniformly_with_replacement(X, len(X)) for X in Xhs]

        ps, rs, f1s = joint_score(P0, Ps, Y0_, Xhs_, W=W, Q=Q)
        for i, row in enumerate(zip(ps, rs, f1s)):
            data[i].append(row)

    ret = []
    for dat in data:
        dat = np.array(dat)
        p, r, f1 = dat[0]
        p_l, r_l, f1_l = np.percentile(dat[1:], 100-interval, 0)
        p_r, r_r, f1_r = np.percentile(dat[1:], interval, 0)

        ret.append(Score(
            p, r, f1,
            p_l, r_l, f1_l,
            p_r, r_r, f1_r,))

    return ret

def compute_variance(Ps, Xhs, Ws=None, Qs=None):
    r"""
    Computes variance using the following formula:
    var_i = \sum_{j=1}^n w_j^2/n_j E_j[ p_i^2 f^2/q_i^2 - \pi_{ij} p_i f_i / q_i]
    """
    assert len(Ps) == len(Xhs)
    m = len(Ps)

    if Ws is None:
        Ws, _ = compute_weights(Ps, Xhs, "heuristic")
    if Qs is None:
        Qs = construct_proposal_distribution(Ws, Ps)

    # Precompute pi_ij
    ret = []
    for i in range(m):
        P, Q, W = Ps[i], Qs[i], Ws[i]
        pi_i = []
        for j in range(m):
            if W[j] == 0.: continue # just ignore this set.
            pi_ij = _avg(Xhs[j], lambda x, fx: P[x]/Q[x]*fx)
            pi_i.append(pi_ij)

        var = 0.
        for j in range(m):
            if W[j] == 0.: continue # just ignore this set.
            var_ij = _avg(Xhs[j], lambda x, fx: (P[x]/Q[x]*fx)**2 - pi_i[j] * (P[x]/Q[x]*fx))
            var += W[j]**2/len(Xhs[j]) * var_ij
        ret.append(var)
    return ret

def estimate_variance(Ps, Xhs, Ws=None, Qs=None):
    r"""
    Estimates variance using the following formula:
    var_i = \sum_{j!=i}^n w_j^2/n_j E_j[ p_i^2 f^2/q_i^2 - \pi_{ij} p_i f_i / q_i] + w_i^2/n_i E_i[ p_i^2/q_i^2]
    """
    assert len(Ps) == len(Xhs)
    m = len(Ps) - 1

    if Ws is None:
        Ws, _ = compute_weights(Ps, Xhs, "heuristic")
    if Qs is None:
        Qs = construct_proposal_distribution(Ws, Ps)

    # Precompute pi_ij
    pi_i = []
    P, Q, W = Ps[m], Qs[m], Ws[m]
    for j in range(m):
        pi_ij = _avg(Xhs[j], lambda x, fx: P[x]/Q[x]*fx)
        pi_i.append(pi_ij)

    var = 0.
    for j in range(m):
        if W[j] == 0.: continue # just ignore this set.
        var_ij = _avg(Xhs[j], lambda x, fx: (P[x]/Q[x]*fx)**2 - pi_i[j] * (P[x]/Q[x]*fx))
        var += W[j]**2/len(Xhs[j]) * var_ij

    # residual is bounded by E_i[p_i^2 f^2 / q^2] (even if it's a terrible bound).
    var_ii = _sum(P.items(), lambda x, px:  px*(px/Q[x])**2)
    var += W[m]**2/len(Xhs[m])* var_ii

    return var

def estimate_n_samples(Ps, Xhs, Ws=None, Zs=None, Qs=None, target=500, eps=5e-4):
    r"""
    Finds the number of samples to draw to estimate pi_i within eps.
    @target is the targetted effective samples
    """
    m = len(Xhs)
    assert len(Ps) == m + 1
    logger.debug("Estimating n->%d samples, using %d systems", target, len(Xhs))
    if len(Xhs) == 0:
        return target

    if Ws is None or Zs is None:
        # Produce Ws
        Ws, Zs = compute_weights(Ps[:-1], Xhs, "heuristic")
    if Qs is None:
        Qs = construct_proposal_distribution(Ws, Ps[:-1])
    assert len(Ws) == m
    assert len(Zs) == m
    assert len(Qs) == m

    # Adds Xhs
    Xhs = Xhs[:] + [[(None, 1) for _ in range(target)]]

    # Compute the target variance
    target_variance = estimate_variance(Ps[m:], Xhs[m:])
    logger.debug("Target variance is %.3e with %d samples", target_variance, target)

    Ws_new, Zs_new = update_weights(Ps, Xhs, Ws, Zs)
    Qs_new = update_proposal_distribution(Ws_new, Zs_new, Ps, Qs, Zs)

    min_variance = estimate_variance(Ps, Xhs, Ws=Ws_new, Qs=Qs_new)
    logger.debug("Min variance is %.3e with %d samples", min_variance, target)
    assert min_variance <= target_variance
    if min_variance == target_variance:
        return target

    # Now do binary search starting from target.
    lower, upper = 1, target
    while lower < upper-1:
        pivot = int((lower + upper)/2)
        Xhs[-1] = [(None, 1) for _ in range(pivot)]
        Ws_new, Zs_new = update_weights(Ps, Xhs, Ws, Zs)
        Qs_new = update_proposal_distribution(Ws_new, Zs_new, Ps, Qs, Zs)

        var = estimate_variance(Ps, Xhs, Ws=Ws_new, Qs=Qs_new)
        logger.debug("Pivot variance is %.3e with %d samples", var, pivot)

        if var - target_variance < -eps: # lower variance than target
            upper = pivot
        elif var - target_variance > eps:
            lower = pivot
        else:
            break
    return pivot

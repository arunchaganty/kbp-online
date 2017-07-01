#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
More elaborate tests for evaluation routines.
"""
from collections import Counter
import logging

import numpy as np

from . import counter_utils
from .evaluation import simple_precision, simple_recall, joint_precision, pooled_recall, pool_recall, joint_recall
from .sample_util import sample_with_replacement, sample_without_replacement

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

def true_sample_distribution(population_size=1000):
    U = Counter({2*x: 1.0 for x in range(int(np.floor(population_size/2)))})
    return U

def generate_true_sample(num_samples, population_size=1000):
    T = [(2*x, 1.0) for x in range(int(np.floor(population_size/2)))]
    np.random.shuffle(T)
    return T[:num_samples]

def repeat_experiment(estimation_fn, sampling_fn, n_epochs=100, *args, **kwargs):
    ys = []
    for _ in range(n_epochs):
        X = sampling_fn(*args, **kwargs)
        ys.append(estimation_fn(*X))
    return np.array(ys)

def stats(estimation_fn, sampling_fn, n_epochs=100, *args, **kwargs):
    ys = repeat_experiment(estimation_fn, sampling_fn, n_epochs, *args, **kwargs)

    mu = np.mean(ys, 0)
    std = np.std(ys, 0)
    return np.vstack((mu, std))

# Scheme to generate samples:
# - specify a precision and recall.
# - draw recall % from the true set.
# - appropriately draw from the false set to get the desired precision.
def generate_submission(precision=0.3, recall=0.2, population_size=1000):
    """
    Everything with an even id is true (simple scheme to generate an infinitude of true data)
    """
    # Have to draw elements without replacement.
    T = [(2*x, 1.0) for x in range(int(np.floor(population_size/2)))]
    F = [(2*x + 1, 0.0) for x in range(int(np.floor(population_size/2)))]
    np.random.shuffle(T)
    np.random.shuffle(F)

    nT = int(np.floor(len(T) * recall))
    nF = int(np.floor(nT * (1./precision - 1.)))
    assert nF < len(F), "Can't satisfy constraints on true and false elements."
    logger.info("Using %d true and %d false samples", nT, nF)

    X = T[:nT] + F[:nF]
    P = counter_utils.normalize(Counter({x: 1. for x, _ in X}))
    return P, X

def test_generate_submission():
    population_size, precision, recall = 1000, 0.5, 0.2
    P, X = generate_submission(precision, recall, population_size)
    precision_ = sum(P[x] * fx for x, fx in X)
    recall_ = sum(fx for _, fx in X)/(population_size/2)
    assert np.allclose(precision, precision_)
    assert np.allclose(recall, recall_)

def generate_submission_set(precisions, recalls, population_size=1000):
    Ps, Xs = [], []
    for precision, recall in zip(precisions, recalls):
        P, X = generate_submission(precision, recall, population_size)
        Ps.append(P)
        Xs.append(X)
    return Ps, Xs

def test_simple_precision_wr():
    np.random.seed(42)
    population_size, precision, recall = 10000, 0.5, 0.2
    P, X = generate_submission(precision, recall, population_size)
    n_samples = 500
    Xh = sample_with_replacement(P, n_samples, X=X)
    precision_ = simple_precision([Xh])[0]
    print (precision, precision_)
    assert np.allclose(precision, precision_, atol=5e-2)

def test_simple_precision_wor():
    np.random.seed(42)
    population_size, precision, recall = 10000, 0.5, 0.2
    P, X = generate_submission(precision, recall, population_size)
    n_samples = 500
    Xh = sample_without_replacement(P, n_samples, X=X)
    precision_ = simple_precision([Xh])[0]
    print (precision, precision_)
    assert np.allclose(precision, precision_, atol=5e-2)

def test_simple_recall():
    np.random.seed(41)
    population_size, precision, recall = 10000, 0.5, 0.2
    n_samples = 500

    P, _ = generate_submission(precision, recall, population_size)
    U = true_sample_distribution(population_size)
    Y0 = [(x, 1.0 if x in P and P[x] > 0 else 0.) for x, _ in generate_true_sample(n_samples, population_size)]
    recall_ = simple_recall(U, [Y0])[0]
    assert np.allclose(recall, recall_, atol=5e-2)

def test_joint_precision_wr():
    np.random.seed(42)
    n_samples = 10000
    population_size, precisions, recalls = 10000, [0.5, 0.3, 0.7], [0.2, 0.1, 0.3]
    Ps, Xs = generate_submission_set(precisions, recalls, population_size)
    Xhs = [sample_with_replacement(P, n_samples, X=X) for P, X in zip(Ps, Xs)]
    precisions_ = joint_precision(Ps, Xhs)
    print(precisions_)
    assert np.allclose(precisions, precisions_, atol=5e-2)

def test_joint_precision_wor():
    np.random.seed(42)
    population_size, precisions, recalls = 1000, [0.5, 0.3, 0.7], [0.2, 0.1, 0.3]
    n_samples = 100
    Ps, Xs = generate_submission_set(precisions, recalls, population_size)
    Xhs = [sample_without_replacement(P, n_samples, X=X) for P, X in zip(Ps, Xs)]
    precisions_ = joint_precision(Ps, Xhs)
    print(precisions_)
    assert np.allclose(precisions, precisions_, atol=5e-2)

def true_pooled_recall(U, P):
    r"""
    Computes Pr(x \in Y_i | x \in Y) = P(Y_i)/P(Y)
    """
    m = len(P)
    Z = 0.
    for n, x in enumerate(U):
        gx = 1.0 if any(x in P[i] and P[i][x] > 0. for i in range(m)) else 0.
        Z += (U[x]*gx - Z)/(n+1)

    nus = []
    for i in range(m):
        nu_i = 0.
        for n, x in enumerate(U):
            gxi = 1.0 if x in P[i] and P[i][x] > 0 else 0.
            nu_i += (U[x]*gxi - nu_i)/(n+1)
        nus.append(nu_i/Z)
    return nus

def test_pooled_recall_wr():
    np.random.seed(42)
    n_samples = 100
    population_size, precisions, recalls = 1000, [0.5, 0.3, 0.7], [0.2, 0.1, 0.3]
    Ps, Xs = generate_submission_set(precisions, recalls, population_size)
    U = true_sample_distribution(population_size)
    pooled_recalls = true_pooled_recall(U, Ps)

    pooled_recalls_ = pooled_recall(U, Ps, Xs)
    print("nu_i", pooled_recalls)
    print("nuh_i", pooled_recalls_)
    assert np.allclose(pooled_recalls, pooled_recalls_, atol=1e-1)

    Xhs = [sample_with_replacement(P, n_samples, X=X) for P, X in zip(Ps, Xs)]
    pooled_recalls_ = pooled_recall(U, Ps, Xhs)
    print("nu_i", pooled_recalls)
    print("nuh_i", pooled_recalls_)
    assert np.allclose(pooled_recalls, pooled_recalls_, atol=1e-1)

def test_pool_recall():
    np.random.seed(42)
    n_samples = 100
    population_size, precisions, recalls = 1000, [0.5, 0.3, 0.7], [0.2, 0.1, 0.3]
    Ps, _ = generate_submission_set(precisions, recalls, population_size)
    U = true_sample_distribution(population_size)

    Y = [[(x, 1.0 if x in P and P[x] > 0 else 0.) for x, _ in sorted(U.items())] for P in Ps]
    pool_recalls = pool_recall(U, Y)

    Y0 = [[(x, 1.0 if x in P and P[x] > 0 else 0.) for x, _ in generate_true_sample(n_samples, population_size)] for P in Ps]
    pool_recalls_ = pool_recall(U, Y0)
    print("theta_i", pool_recalls)
    print("thetah_i", pool_recalls_)
    assert np.allclose(pool_recalls, pool_recalls_, atol=1e-1)

def test_joint_recall():
    np.random.seed(42)
    n_samples = 500
    population_size, precisions, recalls = 10000, [0.5, 0.3, 0.7], [0.2, 0.1, 0.3]
    Ps, Xs = generate_submission_set(precisions, recalls, population_size)
    U = true_sample_distribution(population_size)

    Y = [[(x, 1.0 if x in P and P[x] > 0 else 0.) for x, _ in sorted(U.items())] for P in Ps]

    recalls_ = joint_recall(U, Ps, Y, Xs)
    print("rho_i", recalls)
    print("rhoh_i", recalls_)
    assert np.allclose(recalls, recalls_, atol=1e-1)

    Y0 = [[(x, 1.0 if x in P and P[x] > 0 else 0.) for x, _ in generate_true_sample(n_samples, population_size)] for P in Ps]
    Xhs = [sample_with_replacement(P, n_samples, X=X) for P, X in zip(Ps, Xs)]

    recalls_ = simple_recall(U, Y0)
    print("rho(s)_i", recalls)
    print("rhoh(s)_i", recalls_)
    assert np.allclose(recalls, recalls_, atol=1e-1)

    recalls_ = joint_recall(U, Ps, Y0, Xhs)
    print("rho_i", recalls)
    print("rhoh_i", recalls_)
    assert np.allclose(recalls, recalls_, atol=1e-1)

def test_joint_precision_statistical():
    np.random.seed(42)
    n_samples = 1000
    population_size, precisions, recalls = 10000, [0.5, 0.3, 0.7, 0.6, 0.4, 0.2], [0.2, 0.1, 0.3, 0.3, 0.2, 0.1]

    Ps, Xs = generate_submission_set(precisions, recalls, population_size)

    def _sample():
        Xhs = [sample_without_replacement(P, n_samples, X=X) for P, X in zip(Ps, Xs)]
        return Ps, Xhs

    def _evaluate(Ps, Xhs):
        return simple_precision(Xhs) + joint_precision(Ps, Xhs)

    print(stats(_evaluate, _sample, 100))

def test_joint_recall_statistical():
    np.random.seed(42)
    n_samples = 1000
    population_size, precisions, recalls = 10000, [0.5, 0.3, 0.7, 0.6, 0.4, 0.2], [0.2, 0.1, 0.3, 0.3, 0.2, 0.1]

    Ps, Xs = generate_submission_set(precisions, recalls, population_size)
    U = true_sample_distribution(population_size)

    def _sample():
        Xhs = [sample_without_replacement(P, n_samples, X=X) for P, X in zip(Ps, Xs)]
        Y0 = [[(x, 1.0 if x in P and P[x] > 0 else 0.) for x, _ in generate_true_sample(n_samples, population_size)] for P in Ps]
        return Y0, Xhs

    def _evaluate(Y0, Xhs):
        return simple_recall(U, Y0) + joint_recall(U, Ps, Y0, Xhs)

    print(stats(_evaluate, _sample, 100))

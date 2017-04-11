#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
More elaborate tests for evaluation routines.
"""
import sys
from collections import Counter
from functools import reduce
import logging

import numpy as np

from . import counter_utils
from .evaluation import simple_precision, simple_recall, pooled_precision

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
    P = counter_utils.normalize(Counter({x: 1./len(X) for x, _ in X}))
    return P, X

def test_generate_submission():
    population, precision, recall = 1000, 0.5, 0.2
    P, X = generate_submission(population, precision, recall)
    precision_ = sum(P[x] * fx for x, fx in X)
    recall_ = sum(fx for _, fx in X)/(population/2)
    assert np.allclose(precision, precision_)
    assert np.allclose(recall, recall_)

def generate_submission_set(precisions, recalls, population_size=1000):
    Ps, Xs = [], []
    for precision, recall in zip(precisions, recalls):
        P, X = generate_submission(precision, recall, population_size)
        Ps.append(P)
        Xs.append(X)
    return Ps, Xs

def sample_with_replacement(P, X, num_samples):
    """
    Draw num_samples from X using the distribution P.
    @X: is a list of tuples (x, label(x)).
    @P: is a counter with keys x from X.
    @returns a list of elements from X.
    """
    P_ = [P[x] for x, _ in X]
    assert abs(sum(P_) - 1.) < 1e-6

    Xh_ = np.random.multinomial(num_samples, P_)
    Xh = [X[i] for i, ni in enumerate(Xh_) for _ in range(ni)]
    assert len(Xh) == num_samples
    return Xh

def sample_without_replacement(P, X, num_samples):
    """
    Draw num_samples from X using the distribution P without replacement.
    @X: is a list of tuples (x, label(x)).
    @P: is a counter with keys x from X.
    @returns a list of elements from X.
    """
    P_ = np.array([P[x] for x,_ in X])
    assert abs(sum(P_) - 1.) < 1e-6

    U = np.random.rand(len(X))
    ixs = np.argsort(-P_**U)
    Xh = [X[i] for i in ixs[:num_samples]]
    assert len(Xh) == num_samples
    return Xh

def test_simple_precision_wr():
    np.random.seed(42)
    population, precision, recall = 1000, 0.5, 0.2
    P, X = generate_submission(precision, recall, population)
    n_samples = 100
    Xh = sample_with_replacement(P, X, n_samples)
    precision_ = simple_precision([P], [Xh])[0]
    assert np.allclose(precision, precision_, atol=1e-1)

def test_simple_precision_wor():
    np.random.seed(42)
    population, precision, recall = 1000, 0.5, 0.2
    P, X = generate_submission(precision, recall, population)
    n_samples = 100
    Xh = sample_without_replacement(P, X, n_samples)
    precision_ = simple_precision([P], [Xh])[0]
    assert np.allclose(precision, precision_, atol=1e-1)

def test_simple_recall():
    np.random.seed(41)
    population, precision, recall = 1000, 0.5, 0.2
    n_samples = 100

    P, X = generate_submission(precision, recall, population)
    U = true_sample_distribution(population)
    Y0 = generate_true_sample(n_samples, population)
    recall_ = simple_recall(U, [P], [X], Y0)[0]
    assert np.allclose(recall, recall_, atol=1e-1)

def test_pooled_precision_wr():
    np.random.seed(42)
    n_samples = 100
    population, precisions, recalls = 1000, [0.5, 0.3, 0.7], [0.2, 0.1, 0.3]
    Ps, Xs = generate_submission_set(precisions, recalls, population)
    Xhs = [sample_with_replacement(P, X, n_samples) for P, X in zip(Ps, Xs)]
    precisions_ = pooled_precision(Ps, Xhs)
    print(precisions_)
    assert np.allclose(precisions, precisions_, atol=1e-1)

def test_pooled_precision_wor():
    np.random.seed(42)
    n_samples = 100
    population, precisions, recalls = 1000, [0.5, 0.3, 0.7], [0.2, 0.1, 0.3]
    Ps, Xs = generate_submission_set(precisions, recalls, population)
    Xhs = [sample_without_replacement(P, X, n_samples) for P, X in zip(Ps, Xs)]
    precisions_ = pooled_precision(Ps, Xhs)
    print(precisions_)
    assert np.allclose(precisions, precisions_, atol=1e-1)

def test_pooled_recall():
    pass

def test_pool_recall():
    pass

def test_recall():
    pass

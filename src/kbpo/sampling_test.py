#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to test the unbiasedness and variance of our sampling routines.
"""
import csv
import sys
from collections import namedtuple
from functools import reduce
import logging

import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

# TODO: Maybe I need to mirror sampling?

# TODO: Mirror structure of my actual samples.
def generate_samples(population_size=200, num_samples=100, precision=0.3):
    samples = set(np.random.randint(0, population_size, num_samples))
    #weights = np.random.rand(len(samples))
    weights = np.ones(len(samples))
    labels = np.random.rand(len(samples)) > (1-precision)
    return [(x, (w, l)) for x, w, l in zip(samples, weights, labels)]

def sample_stats(sets):
    logger.info("Sampled %d sets with %s elements, %s of which are true", len(sets), [len(X) for X in sets], [sum(int(l) for _, (_, l) in X) for X in sets])
    sets = [set(x for x, _ in X) for X in sets]

    for i, A in enumerate(sets):
        X = reduce(set.union, [B for j, B in enumerate(sets) if j != i], set())
        logging.info("Overlap between %d and -%d is %d elements", i, i, len(A.intersection(X)))

def generate_sample_sets(num_sets, **kwargs):
    """
    Generate @num_sets of samples of elements using @generate_samples.
    """
    sets = [generate_samples(**kwargs) for _ in range(num_sets)]
    return sets

def test_generate_samples():
    np.random.seed(42)
    sets = generate_sample_sets(3, population_size=200, num_samples=100, precision=0.3)
    sample_stats(sets)
    assert len(sets) == 3, "Sampled the wrong number of sets"
    assert all(len(x) < 100 for x in sets), "Sets contain too many elements"

# Compute the actual unbiased metric.
def evaluate_metric(f, X):
    """
    Evaluates the metric @f on every element of the set @X.
    """
    return sum(w*f(l) for _, (w, l) in X)/sum(w for _, (w, _) in X)

# Construct the pseudo-sampler
def sample_with_replacement(X, num_samples=200):
    """
    Sample elements of X with replacement.
    """
    W = sum(w for _, (w,_) in X)
    P = [w/W for _, (w,_) in X]
    X_ = list(np.random.multinomial(num_samples, P))

    X_ = sum(([(X[i][0], (1.0, X[i][1][1])) for _ in range(n)] for i, n in enumerate(X_) if n > 0), [])
    return X_

def sample_without_replacement(X, num_samples=200):
    """
    Sample elements of X with replacement.
    """
    X = sorted(X, key=lambda k: np.random.random()**k[1][0])
    X_ = [(x,(1.0, l)) for x, (_, l) in X[:num_samples]]
    return X_

def importance_reweight(X, Y, Y_):
    """
    Use samples from Y_ to estimate metrics on X.
    """
    X = {x: wl for x, wl in X}
    Wx = sum(w for w, _ in X.values())
    Y = {y: wl for y, wl in Y}
    Wy = sum(w for w, _ in Y.values())

    X_ = []
    # For every element of Y_
    for y, (w,l) in Y_:
        if y not in X: continue
        # compute p(x) and q(x) and add them up

        p = X[y][0]/Wx
        q = Y[y][0]/Wy

        # Note, that this estimation is *STILL* biased because support of X
        # and support of Y are different.

        X_.append((y, (p/q * w, l)))
    return X_

def sample_with_importance(X, Y, sampler, **kwargs):
    """
    Sample for X using samples from Y
    """
    Y_ = sampler(Y, **kwargs)
    return importance_reweight(X, Y, Y_)

def statistical_estimate(f, X, sampler, n_repeats=100, correction=False, **kwargs):
    fXs = []
    fX = evaluate_metric(f, X)
    for _ in range(n_repeats):
        X_ = sampler(X, **kwargs)
        fXs.append(evaluate_metric(f, X_) - fX)
    fXs = np.array(fXs)
    mean, std = np.mean(fXs), np.std(fXs)
    if correction:
        std = std * np.sqrt(1 - len(X_)/len(X))
    return mean, std

# Actually call the code.
def do_test(args):
    np.random.seed(args.seed)

    #sets = generate_sample_sets(args.num_sets, population_size=args.num_population, num_samples=args.num_instances)
    population = list(range(1000))
    labels = np.random.rand(len(population)) > (1-0.3)
    Wx = np.random.rand(len(population))
    Wy = np.random.rand(len(population))
    Wz = np.random.rand(len(population))

    X = [(x, (Wx[x], labels[x])) for x in population]
    Y = [(y, (Wy[y], labels[y])) for y in population]
    Z = [(z, (Wz[z], labels[z])) for z in population]
    sets = [X, Y, Z]

    sample_stats(sets)

    f = int
    for i, X in enumerate(sets):
        print("Metric over {} is: {:.3f}".format(i, evaluate_metric(f, X)))
        print("w/ replacement: {:.3f} (± {:.3f})".format(*statistical_estimate(f, X, sample_with_replacement)))
        print("w/o replacement: {:.3f} (± {:.3f})".format(*statistical_estimate(f, X, sample_without_replacement, correction=True)))

    # Importance reweighting
    for i, X in enumerate(sets):
        for j, Y in enumerate(sets):
            print("{} for {} w/ replacement: {:.3f} (± {:.3f})".format(j, i, *statistical_estimate(f, X, lambda X_, **kwargs: sample_with_importance(X_, Y, sample_with_replacement, **kwargs))))
            print("{} for {} w/o replacement: {:.3f} (± {:.3f})".format(j, i, *statistical_estimate(f, X, lambda X_, **kwargs: sample_with_importance(X_, Y, sample_without_replacement, **kwargs), correction=True)))



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-m', '--mode', choices=["wr", "wor", "monte-carlo"], default="wr", help="Random seed for experiment")
    parser.add_argument('-s', '--seed', type=int, default=42, help="Random seed for experiment")
    parser.add_argument('-ns', '--num-sets', type=int, default=3, help="Number of sets in experiment")
    parser.add_argument('-np', '--num-population', type=int, default=10000, help="Number of distinct values of the population")
    parser.add_argument('-ni', '--num-instances', type=int, default=1000, help="Number of instances sampled for each set")
    parser.set_defaults(func=do_test)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

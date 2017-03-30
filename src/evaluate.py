#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to test the unbiasedness and variance of our sampling routines.
"""
import csv
import sys
from collections import namedtuple, Counter
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

def sample_without_replacement(X, num_samples=200, Y=None):
    """
    Sample elements of X with replacement.
    """
    if Y is None:
        X = sorted(X, key=lambda k: np.random.random()**k[1][0])
        X_ = [(x,(1.0, l)) for x, (_, l) in X[:num_samples]]
        return X_

def sample_sets_with_replacement(Xs, num_samples=200):
    Xs_ = []
    for X in Xs:
        X_= sample_with_replacement(X, num_samples)
        Xs_ += X_
    return Xs_

#def distribution_with_replacement(Xs):
#    r"""
#    Returns the distribution of samples under the above sampling scheme.
#    Pr(x) = 1 - \prod_{i} (1-pi(x))
#    """
#    Ps = np.zeros(
#    # Pivot the distribution.
#    Xs = [{i:w}

def sample_sets_without_replacement(Xs, num_samples=200):
    Xs_, seen = [], set([])
    for X in Xs:
        X = [(x, wl) for x, wl in X if x not in seen]
        X_= sample_without_replacement(X, num_samples)
        seen.update(x for x, _ in X_)
        Xs_ += X_
    return Xs_

def importance_reweight(X, P, Q):
    """
    Reweight samples of X as if it were sampled from Q for P.
    """
    return [(x, (P[x]/Q[x], l)) for x, (_, l) in X]

def restriction(X, R):
    """
    Restricts the values in X to those in R.
    """
    seen = set(x for x, _ in R)
    return [(x, wl) for x, wl in X if x in seen]

def p(X):
    P = Counter()
    for x, (w,_) in X:
        P[x] = w
    return P

def cross_sample(X, Xs, Q, set_sampler, **kwargs):
    """
    Basically create a sample for X using the set_sampler.
    """
    Xs_ = set_sampler(Xs, **kwargs)
    X_ = restriction(Xs_, X)
    return importance_reweight(X_, p(X), Q)


def statistical_estimate(f, X, sampler, n_repeats=1000, correction=False, **kwargs):
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

    # \sX
    population = list(range(1000))
    Ls = np.random.rand(len(population)) > (1-0.3) # More are false than true.

    # Create support sets X_i
    Ss = np.random.rand(args.num_sets, len(population)) < 0.6 # recall of 0.4

    # Create p_i
    Ps = np.random.rand(args.num_sets, len(population))
    Ps[Ss] = 0. # Blot out non-zeros
    Ps = (Ps.T/Ps.sum(1)).T # Normalize
    Q = Ps.sum(0)/len(Ps)

    Xs = [[(i, (p[i], Ls[i])) for i in population if p[i] > 0.]  for p in Ps]
    sample_stats(Xs)

    f = int
    for i, X in enumerate(Xs):
        print("Metric over {} is: {:.3f}".format(i, evaluate_metric(f, X)))
        print("w/ replacement: {:.3f} (± {:.3f})".format(*statistical_estimate(f, X, sample_with_replacement, num_samples=200)))
        print("w/o replacement: {:.3f} (± {:.3f})".format(*statistical_estimate(f, X, sample_without_replacement, correction=True, num_samples=200)))

    # Importance reweighting
    for i, X in enumerate(Xs):
        print("Scheme estimate w/ replacement for {}: {:.3f} (± {:.3f})".format(i, *statistical_estimate(f, X, lambda X_, **kwargs: cross_sample(X_, Xs, Q, sample_sets_with_replacement, **kwargs), num_samples=200)))
        print("Scheme estimate w/o replacement for {}: {:.3f} (± {:.3f})".format(i, *statistical_estimate(f, X, lambda X_, **kwargs: cross_sample(X_, Xs, Q, sample_sets_without_replacement, **kwargs), num_samples=200)))

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

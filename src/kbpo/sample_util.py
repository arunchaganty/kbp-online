"""
Sampling utilities
"""
import logging
import numpy as np
from collections import Counter

from .counter_utils import normalize

logger = logging.getLogger(__name__)

def kl(p, q):
    """Kullback-Leibler divergence D(P || Q) for discrete distributions
    Parameters
    From: https://gist.github.com/swayson/86c296aa354a555536e6765bbe726ff7
    ----------
    p, q : array-like, dtype=float, shape=n
    Discrete probability distributions.
    """
    p = np.asarray(p, dtype=np.float)
    q = np.asarray(q, dtype=np.float)

    return np.sum(np.where(p != 0, p * np.log(p / q), 0))

def sample_uniformly_with_replacement(X, num_samples):
    """
    Draw num_samples from X using the uniform distribution.
    @X: is a list of tuples (x, label(x)).
    @P: is a counter with keys x from X.
    @returns a list of elements from X.
    """
    m = len(X)

    Xh_ = np.random.multinomial(num_samples, np.ones(m)/m)
    Xh = [X[i] for i, ni in enumerate(Xh_) for _ in range(ni)]
    assert len(Xh) == num_samples
    return Xh

def sample_with_replacement(P, num_samples, X=None):
    """
    Draw num_samples from X using the distribution P.
    @X: is a list of tuples (x, label(x)).
    @P: is a counter with keys x from X.
    @returns a list of elements from X.
    """
    if X is not None:
        assert len(X) == len(P), "Distribution does not match X"

    if X is None:
        X, P_ = zip(*P.items())
        P_ = P_
    else:
        P_ = [P[x] for x, _ in X]
    assert abs(sum(P_) - 1.) < 1e-6

    ixs = list(range(len(X)))
    Xh = [X[i] for i in np.random.choice(ixs, num_samples, replace=True, p=P_)]
    assert len(Xh) == num_samples
    return Xh

def test_sample_with_replacement():
    n_samples = 100000
    np.random.seed(42)
    P = Counter({'a': 0.4, 'b': 0.3, 'c': 0.2, 'd': 0.1})
    samples = sample_with_replacement(P, n_samples)

    assert len(samples) == n_samples
    P_ = Counter(samples)
    P_ = normalize(P_)
    assert np.allclose([P['a'], P['b'], P['c'], P['d']], [P_['a'], P_['b'], P_['c'], P_['d']], 5e-2)

    X = [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
    samples = sample_with_replacement(P, n_samples, X)

    assert len(samples) == n_samples
    P_ = Counter(x for x, _ in samples)
    P_ = normalize(P_)
    assert np.allclose([P['a'], P['b'], P['c'], P['d']], [P_['a'], P_['b'], P_['c'], P_['d']], 5e-2)

def sample_without_replacement(P, num_samples, X=None):
    """
    Draw num_samples from X using the distribution P without replacement.
    @X: is a list of tuples (x, label(x)).
    @P: is a counter with keys x from X.
    @returns a list of elements from X.
    """
    if X is not None:
        assert len(X) == len(P), "Distribution does not match X"
    if len(P) < num_samples:
        logger.warning("Not enough elements to meaningfully sample without replacement")
        if X is not None:
            return X
        else:
            return list(P.keys())

    if X is None:
        X, P_ = zip(*P.items())
    else:
        P_ = [P[x] for x,_ in X]
    assert abs(sum(P_) - 1.) < 1e-6

    # Sample from P_
    ixs = list(range(len(X)))
    Xh = [X[i] for i in np.random.choice(ixs, num_samples, replace=False, p=P_)]
    assert len(Xh) == num_samples
    return Xh

def test_sample_without_replacement():
    population = 100
    n_samples = 10000
    n_per_samples = 10
    np.random.seed(42)

    syms = list(range(population))
    P = Counter({sym:prob for sym, prob in zip(syms, np.random.random(population))})
    P = normalize(P)

    P_ = Counter()
    for _ in range(n_samples):
        samples = sample_without_replacement(P, n_per_samples)
        assert len(samples) == n_per_samples
        P_.update(samples)
    P_ = normalize(P_)

    # KL because this is a harder comparison to make
    dist = kl([P[sym] for sym in syms], [P_[sym] for sym in syms])
    assert dist < 1e-2

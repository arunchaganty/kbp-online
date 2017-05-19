"""
Sampling utilities
"""
import logging
import numpy as np
from collections import Counter

from .counter_utils import normalize

logger = logging.getLogger(__name__)

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
        P_ = np.array(P_)
    else:
        P_ = [P[x] for x, _ in X]
    assert abs(sum(P_) - 1.) < 1e-6

    Xh_ = np.random.multinomial(num_samples, P_)
    Xh = [X[i] for i, ni in enumerate(Xh_) for _ in range(ni)]
    assert len(Xh) == num_samples
    return Xh

def test_sample_with_replacement():
    np.random.seed(42)
    P = Counter({'a': 0.4, 'b': 0.3, 'c': 0.2, 'd': 0.1})
    samples = sample_with_replacement(P, 10000)

    assert len(samples) == 10000
    P_ = Counter(samples)
    P_ = normalize(P_)
    assert np.allclose([P['a'], P['b'], P['c'], P['d']], [P_['a'], P_['b'], P_['c'], P_['d']], 1e-1)

    X = [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
    samples = sample_with_replacement(P, 10000, X)

    assert len(samples) == 10000
    P_ = Counter(x for x, _ in samples)
    P_ = normalize(P_)
    assert np.allclose([P['a'], P['b'], P['c'], P['d']], [P_['a'], P_['b'], P_['c'], P_['d']], 1e-1)


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
        return list(P.keys())

    if X is None:
        X, P_ = zip(*P.items())
        P_ = np.array(P_)
    else:
        P_ = np.array([P[x] for x,_ in X])
    assert abs(sum(P_) - 1.) < 1e-6

    U = np.random.rand(len(X))
    ixs = np.argsort(-P_**U)
    Xh = [X[i] for i in ixs[:num_samples]]
    assert len(Xh) == num_samples
    return Xh

def test_sample_without_replacement():
    np.random.seed(42)
    P = Counter({'a': 0.4, 'b': 0.3, 'c': 0.2, 'd': 0.1})

    P_ = Counter()
    for _ in range(5000):
        samples = sample_without_replacement(P, 2)
        assert len(samples) == 2
        P_.update(samples)
    P_ = normalize(P_)
    assert np.allclose([P['a'], P['b'], P['c'], P['d']], [P_['a'], P_['b'], P_['c'], P_['d']], 3e-1) # This is larger because sampling is biased...

    X = [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
    P_ = Counter()
    for _ in range(5000):
        samples = sample_without_replacement(P, 2, X)
        assert len(samples) == 2
        P_.update(x for x, _ in samples)
    P_ = normalize(P_)
    assert np.allclose([P['a'], P['b'], P['c'], P['d']], [P_['a'], P_['b'], P_['c'], P_['d']], 3e-1) # This is larger because sampling is biased...

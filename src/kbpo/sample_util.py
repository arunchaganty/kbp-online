"""
Sampling utilities
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)

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
    if len(X) < num_samples:
        logger.warning("Not enough elements to meaningfully sample without replacement")
        return X

    P_ = np.array([P[x] for x,_ in X])
    assert abs(sum(P_) - 1.) < 1e-6

    U = np.random.rand(len(X))
    ixs = np.argsort(-P_**U)
    Xh = [X[i] for i in ixs[:num_samples]]
    assert len(Xh) == num_samples
    return Xh


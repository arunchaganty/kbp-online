#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Useful functions for Counter manipulation.
"""

from collections import Counter

def scale(cntr, factor):
    cntr_ = Counter()
    for key, value in cntr.items():
        cntr_[key] = value * factor
    return cntr_

def normalize(cntr):
    return scale(cntr, 1./sum(cntr.values()))

def equals(cntr, cntr_):
    keys = set(cntr.keys()).union(set(cntr_.keys()))
    for key in keys:
        if key not in cntr or key not in cntr_:
            return False
        elif cntr[key] != cntr_[key]:
            return False
    return True

def test_equals():
    assert equals(Counter([1,1,3,4]),Counter([1,3,1,4]))
    assert not equals(Counter([1,1,3,4]),Counter([1,3,3,4]))

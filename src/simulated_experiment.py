#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runs a simulated experiment on previous TAC-KBP years.
"""

import pdb
import os
import csv
import sys
import logging
from collections import Counter

import numpy as np

from tqdm import tqdm
from kbpo.data import load_queries, load_gold, load_output, Provenance, EvaluationEntry, OutputEntry
from kbpo.util import macro, micro
from kbpo.analysis import k, kn, get_key, project_gold, project_output, compute_entity_scores
from kbpo.counter_utils import normalize
from kbpo.test_evaluation import sample_with_replacement, sample_without_replacement
from kbpo.evaluation import weighted_score, simple_score, joint_score

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def load_data(args, key_fn=k):
    Q = load_queries(args.queries)
    gold = load_gold(args.gold, Q)
    outputs = {}

    for fname in os.listdir(args.preds):
        if not fname.endswith(".txt"): continue
        runid = fname.split(".")[0]
        logger.info("Loading output for %s", runid)

        with open(os.path.join(args.preds, fname)) as f:
            outputs[runid] = load_output(f, Q)
        break
    logger.info("Loaded output for %d systems", len(outputs))
    return Q, gold, outputs

def transform_output(Q, gold, outputs, mode="closed-world"):
    """
    Transform output from the official evaluation files to appropriately
    score output.
    In particular, this function transforms the input to include all
    true entries for a particular relation as a way of handling recall
    problems.
    """
    G, Gr = project_gold(Q, gold, mode)
    # The list of all true items are in Gr.
    Y = [(key, 1.0) for (_, key), value in Gr.items() if value > 0]
    # Uniformly weigh entities.
    U = Counter({x:1./len(xs) for fills in G.values() for eq, xs in fills.items() for x in xs if eq > 0.})

    Rs, Xs, Ps  = [], [], []
    for run_id, output in outputs.items():
        Rs.append(run_id) # Helps keep track of performance.
        O = project_output(Q, Gr, output, mode)
        X = []
        # To handle the problem with missing mentions and its effect on
        # recall, if the system gets one instanec for a fill, it's
        # artificially made to get _all_ of them.
        # We account for its effect on precision by dividing by the
        # number of correct fills.
        P = Counter({})
        for entity, fills in O.items():
            for eq, xs in fills.items():
                if eq == 0: # the incorrect fills; do not augment.
                    X.extend([(x, 0.0) for x in xs])
                    P.update({x: 1. for x in xs})
                else: # Augment keys with things in P.
                    xs_ = G[entity][eq]
                    X.extend([(x, 1.0) for x in xs_])
                    P.update({x: 1./len(xs_) for x in xs_})
        Xs.append(X)
        P = normalize(P)
        Ps.append(normalize(P))
    return U, Y, Rs, Ps, Xs

def _test_input():
    Q = {'s1': 's1', 's2': 's2', 's3':'s3'}
    gold = [
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d1',1,2)], 'o0', [], 'C', 'C', 0, 0),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d1',1,2)], 'o1', [], 'C', 'C', 1, 1),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d2',1,2)], 'o1', [], 'C', 'C', 1, 1),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d3',1,2)], 'o1', [], 'C', 'C', 1, 1),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d1',1,2)], 'o2', [], 'C', 'C', 2, 2),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d2',1,2)], 'o2', [], 'C', 'C', 2, 2),
        EvaluationEntry(1, 's2', 's2','r1', [Provenance('d1',1,2)], 'o0', [], 'C', 'C', 0, 0),
        EvaluationEntry(1, 's2', 's2','r1', [Provenance('d1',1,2)], 'o3', [], 'C', 'C', 3, 3),
        EvaluationEntry(1, 's2', 's2','r1', [Provenance('d2',1,2)], 'o3', [], 'C', 'C', 3, 3),
        ]
    output = [
        OutputEntry('s1', 's1','r1', 'test', [Provenance('d1',1,2)], 'o0', 'type', [], 1.0), # '0'),
        #OutputEntry('s1', 's1','r1', 'test', [Provenance('d1',1,2)], 'o1', 'type', [], 1.0), # '1'),
        OutputEntry('s1', 's1','r1', 'test', [Provenance('d1',1,2)], 'o2', 'type', [], 1.0), # '2'),
        OutputEntry('s2', 's2','r1', 'test', [Provenance('d1',1,2)], 'o0', 'type', [], 1.0), # '0'),
        OutputEntry('s2', 's2','r1', 'test', [Provenance('d2',1,2)], 'o3', 'type', [], 1.0), # '3'),
        ]
    return Q, gold, [output]

def test_transform_output():
    Q, gold, outputs = _test_input()
    S, C, T = compute_entity_scores(Q, gold, outputs[0])
    p, r, f1 = micro(S, C, T)
    print("official", p, r, f1)

    U, Y, _, Ps, Xs, = transform_output(Q, gold, {'test': outputs[0]})
    ps, rs, f1s = weighted_score(U, Ps, Y, Xs)
    p_, r_, f1_ = ps[0], rs[0], f1s[0]
    print("weighted", p_, r_, f1_)

    assert np.allclose([p, r, f1], [p_,r_,f1_], 1e-2)

def test_transform_output_sample():
    np.random.seed(42)

    Q, gold, outputs = _test_input()
    U, Y, _, Ps, Xs, = transform_output(Q, gold, {'test':outputs[0]})
    ps, rs, f1s = weighted_score(U, Ps, Y, Xs)
    p, r, f1 = ps[0], rs[0], f1s[0]
    print("weighted", p, r, f1)

    # Draw samples.
    n_samples = 1000
    U_ = normalize(Counter({x: 1.0 for x in U})) # uniform distribution is what we really can sample from.
    Y0 = sample_with_replacement(normalize(U_), Y, n_samples)
    Xhs = [sample_with_replacement(P, X, n_samples) for P, X in zip(Ps, Xs)]

    ps, rs, f1s = simple_score(U, Ps, Y0, Xhs)
    p_, r_, f1_ = ps[0], rs[0], f1s[0]
    print("simple", p_, r_, f1_)
    assert np.allclose([p, r, f1], [p_,r_,f1_], 5e-2)

def simulate_pooling(Xs):
    pass

def do_simulate(args):
    Q, gold, outputs = load_data(args)
    _, Gr = project_gold(Q, gold, 'closed-world')
    U, Y, Rs, Ps, Xs = transform_output(Q, gold, outputs)
    precisions, recalls, f1s = weighted_score(U, Ps, Y, Xs)

    for i in range(len(Ps)):
        output = outputs[Rs[i]]
        S, C, T = compute_entity_scores(Q, gold, output)
        #S_, C_, T_ = compute_stats(Gr, Y, Xs[i], Xs_[i])
        #def sym(x,y): 
        #    return "==" if x == y else "<>"
        #for s in S:
        #    print("{}: S({} {} {}), C({} {} {}), T({} {} {})".format(s, S[s], sym(S[s],S_[s]), S_[s], C[s], sym(C[s],C_[s]), C_[s], T[s], sym(T[s],T_[s]),T_[s]))
        #for s in T:
        #    if s not in S:
        #        print(s, S[s], S_[s], C[s], C_[s], T[s], T_[s])
        print("entity score: {:.3f}, {:.3f}, {:.3f}".format(*micro(S, C, T)))
        print("sample score: {:.3f}, {:.3f}, {:.3f}".format(precisions[i], recalls[i], f1s[i]))

    # Measure the true precision and recall values on the entire data.
    # TODO: Pick the top 40 teams for the experiment?
    # Randomly subsample queries to evaluate against
    # For n epochs:
    #   Create a random pool of $n$ elements, not including this system. 
    #   Evaluate scores based on the chosen elements.

if __name__ == "__main__":
    import argparse

    DD = "data/KBP2015_Cold_Start_Slot-Filling_Evaluation_Results_2016-03-31"
    parser = argparse.ArgumentParser(description='Run a simulated experiment to compare stability of previous year scores with different methodologies')
    parser.add_argument('-g', '--gold', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_poolc.assessed.fqec"), help="A list of gold entries")
    parser.add_argument('-q', '--queries', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_queryids.v3.0.txt"), help="A list of queries that were evaluated")
    parser.add_argument('-ps', '--preds', type=str, default=(DD+ "/corrected_runs/"), help="A directory with predicted entries")
    parser.add_argument('-m', '--mode', choices=["pooled", "simple", "ondemand"], default="pooled", help="How scores should be estimated")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Outputs a list of results for every system (true, predicted, stdev)")
    parser.set_defaults(func=do_simulate)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluate submissions on kbpo server.
"""
import pdb
import sys
import csv
import logging

from collections import Counter, defaultdict

import numpy as np

from kbpo import evaluation
from kbpo import db_evaluation as dbe
from kbpo.sample_util import sample_uniformly_with_replacement

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO)

def load_data(args):
    logger.info("Loading data")
    Y0 = dbe.get_exhaustive_samples(args.corpus_tag)
    logger.info("Found %d exhaustive samples", len(Y0))
    Rs, Ps, Xhs = [], [], []
    for submission in dbe.get_submissions():
        Rs.append("relation:{}".format(submission.id))
        Ps.append(dbe.compute_relation_distribution(args.corpus_tag, submission.id))
        Xhs.append(dbe.get_submission_samples(args.corpus_tag, 'relation', submission.id))
        logger.info("Found %d selective relation samples for %d with mass %.2f", len(Xhs[-1]), submission.id,
                sum(Ps[-1][x] for x,_ in Xhs[-1]))

        Rs.append("entity:{}".format(submission.id))
        Ps.append(dbe.compute_entity_distribution(args.corpus_tag, submission.id))
        Xhs.append(dbe.get_submission_samples(args.corpus_tag, 'entity', submission.id))
        logger.info("Found %d selective entity samples for %d with mass %.2f", len(Xhs[-1]), submission.id,
                sum(Ps[-1][x] for x,_ in Xhs[-1]))
    U = Counter(set(x for X in Xhs + [Y0,] for x, fx in X if fx == 1.0)) # uniform for now.
    return Rs, U, Ps, Y0, Xhs

# Actually call the code.
def do_evaluate(args):
    Rs, U, Ps, Y0, Xhs = load_data(args)
    m = len(Rs)

    W = evaluation.compute_weights(Ps, Xhs, "heuristic") # To save computation time (else it's cubic in n!).
    Q = evaluation.construct_proposal_distribution(W, Ps)
    #pdb.set_trace()

    # Bootstrap sample.
    metrics = defaultdict(list)

    if args.mode == "simple":
        ps, rs, f1s = evaluation.simple_score(U, Ps, Y0, Xhs)
    elif args.mode == "joint":
        ps, rs, f1s = evaluation.joint_score(U, Ps, Y0, Xhs, W=W, Q=Q)

    for i in range(m):
        metrics[Rs[i]].append([ps[i], rs[i], f1s[i]])

    for _ in range(args.num_epochs):
        Y0_ = sample_uniformly_with_replacement(Y0, len(Y0))
        Xhs_ = [sample_uniformly_with_replacement(X, len(X)) for X in Xhs]

        if args.mode == "simple":
            ps, rs, f1s = evaluation.simple_score(U, Ps, Y0_, Xhs_)
        elif args.mode == "joint":
            ps, rs, f1s = evaluation.joint_score(U, Ps, Y0_, Xhs_, W=W, Q=Q)
        for i in range(m):
            metrics[Rs[i]].append([ps[i], rs[i], f1s[i]])

    writer = csv.writer(args.output, delimiter="\t")
    writer.writerow(['run_id',
                     'p', 'r', 'f1',
                     'err-p-left', 'err-r-left', 'err-f1-left',
                     'err-p-right', 'err-r-right', 'err-f1-right',
                    ])
    for run_id in sorted(Rs):
        metrics_ = np.array(metrics[run_id])
        p, r, f1 = metrics_[0]
        #p, r, f1 = np.mean(metrics_, 0)
        p_l, r_l, f1_l = np.percentile(metrics_[1:], 5, 0)
        p_r, r_r, f1_r = np.percentile(metrics_[1:], 95, 0)
        #p_l, r_l, f1_l = np.percentile(metrics_, 5, 0)
        #p_r, r_r, f1_r = np.percentile(metrics_, 95, 0)
        writer.writerow([run_id,
                         p, r, f1,
                         p - p_l, r - r_l, f1 - f1_l,
                         p_r - p, r_r - r, f1_r - f1])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Evaluate submissions from the KBPO database')
    parser.add_argument('-m', '--mode', choices=['simple', 'joint'], default='simple', help='Mode to evaluate experiments with')
    parser.add_argument('-t', '--corpus-tag', choices=['kbp2016'], default='kbp2016', help='Evaluation corpus to get scores for')
    parser.add_argument('-n', '--num-epochs', type=int, default=1000, help="Number of epochs to average over")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Outputs a list of results for every system (true, predicted, stdev)")
    parser.set_defaults(func=do_evaluate)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

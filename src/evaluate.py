#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluate submissions on kbpo server.
"""
import sys
import csv
import logging

from kbpo import evaluation
from kbpo import db_evaluation as dbe

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO)

def load_data(args):
    Y0 = dbe.get_exhaustive_samples(args.corpus_tag)
    Rs, Ps, Xhs = [], [], []
    for submission in dbe.get_submissions():
        Rs.append(submission.id)
        Ps.append(dbe.compute_relation_distribution(args.corpus_tag, submission.id))
        Xhs.append(dbe.get_submission_samples(args.corpus_tag, 'relation', submission.id))

        Rs.append(submission.id)
        Ps.append(dbe.compute_entity_distribution(args.corpus_tag, submission.id))
        Xhs.append(dbe.get_submission_samples(args.corpus_tag, 'entity', submission.id))
    U = Counter(set(x for X in Xhs + [Y0,] for x, fx in X if x == 1.0)) # uniform for now.
    return Rs, U, Ps, Y0, Xhs

# Actually call the code.
def do_evaluate(args):
    Rs, U, Ps, Y0, Xhs = load_data(args)
    # TODO: boot strap sample from Y0 and Xhs
    for submission_id in range(1,4):
        logger.info("Instance score of %d is %.3f %.3f %.3f", submission_id, *db_evaluation.score(submission_id, "instance"))
        logger.info("Relation score of %d is %.3f %.3f %.3f", submission_id, *db_evaluation.score(submission_id, "relation"))
        logger.info("Entity score of %d is %.3f %.3f %.3f", submission_id, *db_evaluation.score(submission_id, "entity"))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Evaluate submissions from the KBPO database')
    parser.add_argument('-m', '--mode', choices=['simple', 'joint'], default='simple', help='Mode to evaluate experiments with')
    parser.add_argument('-t', '--corpus-tag', choices=['kbp2016'], default='kbp2016', help='Evaluation corpus to get scores for')
    parser.set_defaults(func=do_evaluate)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

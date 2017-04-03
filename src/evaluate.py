#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to test the unbiasedness and variance of our sampling routines.
"""
import sys
import csv
import logging

from kbpo import evaluation

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO)

# Actually call the code.
def do_evaluate(args):
    for submission_id in range(1,4):
        logger.info("Instance score of %d is %.3f %.3f %.3f", submission_id, *evaluation.score(submission_id, "instance"))
        logger.info("Relation score of %d is %.3f %.3f %.3f", submission_id, *evaluation.score(submission_id, "relation"))
        logger.info("Entity score of %d is %.3f %.3f %.3f", submission_id, *evaluation.score(submission_id, "entity"))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-m', '--mode', choices=["instance", "relation", "entity"], default="instance", help="Evaluation methodology to use")
    parser.add_argument('-s', '--seed', type=int, default=42, help="Random seed for experiment")
    parser.set_defaults(func=do_evaluate)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

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
from tqdm import tqdm

from kbpo import evaluation_api

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO)

def fn(n):
    return "{:0.04f}".format(n)

# Actually call the code.
def do_evaluate(args):
    writer = csv.writer(args.output, delimiter="\t")
    writer.writerow(['run_id',
                     'p', 'r', 'f1',
                     'err-p-left', 'err-r-left', 'err-f1-left',
                     'err-p-right', 'err-r-right', 'err-f1-right',
                    ])
    for system, score in evaluation_api.get_updated_scores(args.corpus_tag, mode=args.mode, num_epochs=args.num_epochs):
        score = score._replace(
            p_left=score.p - score.p_left,
            r_left=score.r - score.r_left,
            f1_left=score.f1 - score.f1_left,
            p_right=-score.p + score.p_right,
            r_right=-score.r + score.r_right,
            f1_right=-score.f1 + score.f1_right,)
        writer.writerow([system,] + [fn(v) for v in score])

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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A scoring script.
"""
import os
import csv
import sys
import logging
from collections import defaultdict

import numpy as np

import ipdb
from tqdm import tqdm
from kbpo.util import EvaluationEntry, OutputEntry, micro, macro, bootstrap, confidence_intervals

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def k(entry):
    return (entry.relation_provenances[0], entry.slot_value) # A cheap way to also correct for linking errors.

def load_queries(fstream):
    Q = {}
    for line in fstream:
        fields = line.split()
        # NOTE: We are considering partial assessments because that's
        # what KBP is doing too.
        ldc_query, cssf_query = fields[:2]
        Q[cssf_query] = ldc_query
    return Q

def load_gold(fstream, Q):
    gold = []
    for line in tqdm(fstream):
        entry = EvaluationEntry.from_line(line)
        if entry.query_id in Q:
            gold.append(entry)
    logger.info("Loaded %d evaluation entries", len(gold))
    return gold

def load_output(fstream, Q = None):
    output = []
    for line in tqdm(fstream):
        entry = OutputEntry.from_line(line)
        if Q is None or entry.query_id in Q:
            output.append(entry)
    logger.info("Loaded %d output entries.", len(output))
    return output

def teamid(runid):
    """
    SF_UMass_IESL1 -> UMass_IESL
    """
    return runid.split("_", 1)[-1][:-1]

def do_stats(args):
    assert os.path.exists(args.preds) and os.path.isdir(args.preds), "{} does not exist or is not a directory".format(args.preds)

    Q = load_queries(args.queries)
    E = sorted(set(Q.values()))

    gold = load_gold(args.gold, Q)
    outputs = {}

    for fname in os.listdir(args.preds):
        if not fname.endswith(".txt"): continue
        runid = fname.split(".")[0]
        logger.info("Loading output for %s", runid)

        with open(os.path.join(args.preds, fname)) as f:
            output = load_output(f)
            if len(output) > 0:
                outputs[runid] = output

    print("Total submissions", len(outputs))
    print("Total entities", len(E))
    print("Total gold outputs", len(set(k(entry) for entry in gold)))
    print("Total unique outputs", len(set(k(entry) for output in outputs.values() for entry in output)))
    print("Total average outputs", sum(len(output) for output in outputs.values())/len(outputs))

if __name__ == "__main__":
    DD = "data/KBP2015_Cold_Start_Slot-Filling_Evaluation_Results_2016-03-31"
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-g', '--gold', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_poolc.assessed.fqec"), help="A list of gold entries")
    parser.add_argument('-q', '--queries', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_queryids.v3.0.man-cmp.txt"), help="A list of queries that were evaluated")

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('stats', help='Evaluate dataset stats')
    command_parser.add_argument('-ps', '--preds', type=str, default=(DD+ "/corrected_runs/"), help="A directory with predicted entries")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.set_defaults(func=do_stats)

    ARGS = parser.parse_args()
    if ARGS.func:
        ARGS.func(ARGS)
    else:
        parser.print_help()
        sys.exit(1)

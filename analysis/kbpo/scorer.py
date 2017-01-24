#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A scoring script.
"""
import sys
import logging

from collections import defaultdict

from tqdm import tqdm
from .util import EvaluationEntry, OutputEntry, micro, macro

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

def load_output(fstream, Q):
    output = []
    for line in tqdm(fstream):
        entry = OutputEntry.from_line(line)
        if entry.query_id in Q:
            output.append(entry)
    logger.info("Loaded %d output entries.", len(output))
    return output

def compute_entity_scores(gold, output, Q):
    """
    @gold is a dictionary of {s: F*_s}.
    F*_s = {f: [m]}

    @pred is dictionary of {s: F_s}.
    F_s = {f: [m]}

    @returns (P, R, F1):
        P = {s: P_s}; P_s = F_s ^ F*_s / F_s
        R = {s: R_s}; R_s = F_s ^ F*_s / F*_s
        F1 = {s: F1_s}; F1_s = 2 P_s R_s / (P_s + R_s)
    """
    G = defaultdict(lambda: defaultdict(set)) # Gold data
    Gr = {} # maps from entry to (s, f)
    for entry in gold:
        s = Q[entry.query_id]
        # Considering inexact queries as correct because these are
        # considered correct as per recall computations.
        f = entry.eq # if (entry.slot_value_label == "C") else 0
        G[s][f].add(k(entry)) # Make a key out of this entry.
        Gr[s, k(entry)] = f

    O = defaultdict(lambda: defaultdict(set)) # Gold data
    for entry in output:
        s = Q[entry.query_id]
        f = Gr[s, k(entry)]
        O[s][f].add(k(entry))

    S, C, T = {}, {}, {} # submitted, correct, total
    for s, Fs in G.items():
        Fs_ = O[s]

        # In the KBP evaluation, we know that only one mention has been
        # returned per purported entity -- thus, if mentions > 1 =>
        # there are duplicate mentions
        S[s] = sum(len(ms) for f, ms in Fs_.items()) #
        # S[s] = sum(1. if f > 0 else len(ms) for f, ms in Fs_.items())
        # What we'd use otherwise.
        C[s] = sum(1. for f in Fs if f > 0 and f in Fs_)
        T[s] = sum(1. for f in Fs if f > 0)

    return S, C, T

def compute_mention_scores(gold, output):
    """
    @gold is a dictionary of {s: F*_s}.
    F*_s = {f: [m]}

    @pred is dictionary of {s: F_s}.
    F_s = {f: [m]}

    @returns (P, R, F1):
        P = {s: P_s}; P_s = F_s ^ F*_s / F_s
        R = {s: R_s}; R_s = F_s ^ F*_s / F*_s
        F1 = {s: F1_s}; F1_s = 2 P_s R_s / (P_s + R_s)
    """
    G = defaultdict(set) # Gold data
    for entry in gold:
        if entry.eq > 0: # it's correct!
            G[entry.relation_provenances[0].doc_id].add(k(entry))

    O = defaultdict(set) # output data
    for entry in output:
        O[entry.relation_provenances[0].doc_id].add(k(entry))

    S, C, T = {}, {}, {} # submitted, correct, total
    for d, Fd in G.items():
        Fd_ = O[d]

        S[d] = len(Fd_)
        C[d] = len(Fd.intersection(Fd_))
        T[d] = len(Fd)

    return S, C, T

def do_entity_evaluation(args):
    Q = load_queries(args.queries)
    gold = load_gold(args.gold, Q)
    output = load_output(args.pred, Q)

    S, C, T = compute_entity_scores(gold, output, Q)

    for s in sorted(S):
        args.output.write("{} {:.04f} {:.04f} {:.04f}\n".format(s, *micro({s:S[s]}, {s:C[s]}, {s:T[s]})))
    args.output.write("micro {:.04f} {:.04f} {:.04f}\n".format(*micro(S,C,T)))
    args.output.write("macro {:.04f} {:.04f} {:.04f}\n".format(*macro(S,C,T)))

def do_mention_evaluation(args):
    Q = load_queries(args.queries)
    gold = load_gold(args.gold, Q)
    output = load_output(args.pred, Q)

    S, C, T = compute_mention_scores(gold, output)

    for s in sorted(S):
        args.output.write("{} {:.04f} {:.04f} {:.04f}\n".format(s, *micro({s:S[s]}, {s:C[s]}, {s:T[s]})))
    args.output.write("micro {:.04f} {:.04f} {:.04f}\n".format(*micro(S,C,T)))
    args.output.write("macro {:.04f} {:.04f} {:.04f}\n".format(*macro(S,C,T)))

if __name__ == "__main__":
    DD = "data/KBP2015_Cold_Start_Slot-Filling_Evaluation_Results_2016-03-31"
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-g', '--gold', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_poolc.assessed.fqec"), help="A list of gold entries")
    parser.add_argument('-q', '--queries', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_queryids.v3.0.man-cmp.txt"), help="A list of queries that were evaluated")

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('entity-evaluation', help='Evaluate a single entry (entity)')
    command_parser.add_argument('-p', '--pred', type=argparse.FileType('r'), required=True, help="A list of predicted entries")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.set_defaults(func=do_entity_evaluation)

    command_parser = subparsers.add_parser('mention-evaluation', help='Evaluate a single entry (mention)')
    command_parser.add_argument('-p', '--pred', type=argparse.FileType('r'), required=True, help="A list of predicted entries")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.set_defaults(func=do_mention_evaluation)

    ARGS = parser.parse_args()
    if ARGS.func:
        ARGS.func(ARGS)
    else:
        parser.print_help()
        sys.exit(1)

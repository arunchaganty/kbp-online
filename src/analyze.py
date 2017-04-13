#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A scoring script.
"""
import os
import csv
import sys
import logging

from tqdm import tqdm
from kbpo.util import micro, macro, confidence_intervals
from kbpo.data import load_queries, load_gold, load_output
from kbpo.analysis import compute_entity_scores, compute_mention_scores, compute_score_matrix, standardize_scores, report_score_matrix, k, kn

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def do_entity_evaluation(args):
    Q = load_queries(args.queries)
    gold = load_gold(args.gold, Q)
    output = load_output(args.pred, Q)

    S, C, T = compute_entity_scores(Q, gold, output, args.mode)

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

def do_compute_intervals(args):
    assert os.path.exists(args.preds) and os.path.isdir(args.preds), "{} does not exist or is not a directory".format(args.preds)

    Q = load_queries(args.queries)
    E = sorted(set(Q.values()))

    gold = load_gold(args.gold, Q)

    writer = csv.writer(args.output, delimiter="\t")
    writer.writerow([
        "system",
        "micro-p", "micro-p-left", "micro-p-right",
        "micro-r", "micro-r-left", "micro-r-right",
        "micro-f1", "micro-f1-left", "micro-f1-right",
        "macro-p", "macro-p-left", "macro-p-right",
        "macro-r", "macro-r-left", "macro-r-right",
        "macro-f1", "macro-f1-left", "macro-f1-right",
        ])

    for fname in os.listdir(args.preds):
        if not fname.endswith(".txt"): continue
        runid = fname.split(".")[0]
        logger.info("Loading output for %s", runid)

        with open(os.path.join(args.preds, fname)) as f:
            output = load_output(f, Q)
            S, C, T = compute_entity_scores(Q, gold, output)

            def compute_metric(E_):
                S_, C_, T_ = {}, {}, {}
                for i, e in enumerate(E_):
                    S_[i], C_[i], T_[i] = S[e], C[e], T[e]
                return micro(S_, C_, T_) + macro(S_, C_, T_)

            # compute bootstrap
            stats = confidence_intervals(E, compute_metric, args.samples, args.confidence)
            writer.writerow([runid, *list(stats.T.flatten())])

def teamid(runid):
    """
    SF_UMass_IESL1 -> UMass_IESL
    """
    return runid.split("_", 1)[-1][:-1]

def do_pooling_bias(args):
    assert os.path.exists(args.preds) and os.path.isdir(args.preds), "{} does not exist or is not a directory".format(args.preds)

    Q = load_queries(args.queries)

    gold = load_gold(args.gold, Q)
    outputs = {}

    for fname in os.listdir(args.preds):
        if not fname.endswith(".txt"): continue
        runid = fname.split(".")[0]
        logger.info("Loading output for %s", runid)

        with open(os.path.join(args.preds, fname)) as f:
            outputs[runid] = load_output(f, Q)
    logger.info("Loaded output for %d systems", len(outputs))

    def make_loo_pool(gold, outputs, runid, mode="closed-world"):
        """
        Create a new gold set which includes only the inputs from all other systems.
        """
        if mode == "closed-world" or "condensed":
            key = k
        elif mode == "anydoc" or "condensed-anydoc":
            key = kn
        else:
            raise ValueError("Unsupported mode: " + mode)

        valid_entries = set([])
        for runid_, output in outputs.items():
            # Making sure UTAustin doesn't make fudge our results
            if runid == runid_ or runid == 'SF_UTAustin1': continue
            valid_entries.update(key(entry) for entry in output)
        gold_ = [entry for entry in gold if key(entry) in valid_entries]
        logger.info("loo pool for %s contains %d entries", runid, len(gold_))
        return gold_

    def make_lto_pool(gold, outputs, runid, mode="closed-world"):
        """
        Create a new gold set which includes only the inputs from all other systems.
        """
        if mode == "closed-world" or "condensed":
            key = k
        elif mode == "anydoc" or "condensed-anydoc":
            key = kn
        else:
            raise ValueError("Unsupported mode: " + mode)

        valid_entries = set([])
        for runid_, output in outputs.items():
            if teamid(runid) == teamid(runid_) or runid == 'SF_UTAustin1': continue
            valid_entries.update(key(entry) for entry in output)
        gold_ = [entry for entry in gold if key(entry) in valid_entries]
        logger.info("lto pool for %s contains %d entries", runid, len(gold_))
        return gold_

    writer = csv.writer(args.output, delimiter="\t")
    writer.writerow([
        "system",
        "micro-p", "micro-r", "micro-f1", "macro-p", "macro-r", "macro-f1",
        "micro-p-loo", "micro-r-loo", "micro-f1-loo", "macro-p-loo", "macro-r-loo", "macro-f1-loo",
        "micro-p-lto", "micro-r-lto", "micro-f1-lto", "macro-p-lto", "macro-r-lto", "macro-f1-lto",
        ])

    rows = []
    for runid, output in tqdm(outputs.items()):
        row = []
        S, C, T = compute_entity_scores(Q, gold, output, args.mode)
        row += micro(S, C, T) + macro(S,C,T)

        S, C, T = compute_entity_scores(Q, make_loo_pool(gold, outputs, runid, args.mode), output, args.mode)
        row += micro(S, C, T) + macro(S,C,T)

        S, C, T = compute_entity_scores(Q, make_lto_pool(gold, outputs, runid, args.mode), output, args.mode)
        row += micro(S, C, T) + macro(S,C,T)

        writer.writerow([runid,] + row)
        args.output.flush()
        rows.append([runid,] + row)

    logger.info("Wrote %d rows of output", len(rows))

    args.output.flush()

def do_standardized_evaluation(args):
    assert os.path.exists(args.preds) and os.path.isdir(args.preds), "{} does not exist or is not a directory".format(args.preds)

    Q = load_queries(args.queries)
    E = sorted(set(Q.values()))

    gold = load_gold(args.gold, Q)
    scores = {}

    for fname in os.listdir(args.preds):
        if not fname.endswith(".txt"): continue
        runid = fname.split(".")[0]
        logger.info("Loading output for %s", runid)

        if runid == "LDC": continue

        with open(os.path.join(args.preds, fname)) as f:
            output = load_output(f, Q)
            scores[runid] = compute_entity_scores(Q, gold, output)

    X_rs = compute_score_matrix(scores, E)
    report_score_matrix(X_rs, args.output_vis, sorted(scores), sorted(Q))

    writer = csv.writer(args.output, delimiter="\t")
    writer.writerow([
        "system",
        "macro-sf1", "macro-sf1-left", "macro-sf1-right",
        ])

    def compute_metric(E_):
        scores_ = {}
        for runid in scores:
            S, C, T = scores[runid]
            S_, C_, T_ = {}, {}, {}
            for i, e in enumerate(E_):
                S_[i], C_[i], T_[i] = S[e], C[e], T[e]
            scores_[runid] = S_, C_, T_
        X_rs = compute_score_matrix(scores_, E_)
        ys = standardize_scores(X_rs)
        return ys

    # compute bootstrap
    stats = confidence_intervals(E, compute_metric, args.samples, args.confidence)
    logger.info("stats: %d, %d", *stats.shape)
    stats = stats.T
    for i, runid in enumerate(sorted(scores)):
        writer.writerow([runid, *list(stats[i])])

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    DD = "data/KBP2015_Cold_Start_Slot-Filling_Evaluation_Results_2016-03-31"
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-g', '--gold', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_poolc.assessed.fqec"), help="A list of gold entries")
    parser.add_argument('-q', '--queries', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_queryids.v3.0.txt"), help="A list of queries that were evaluated")

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('entity-evaluation', help='Evaluate a single entry (entity)')
    command_parser.add_argument('-p', '--pred', type=argparse.FileType('r'), required=True, help="A list of predicted entries")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.add_argument('-m', '--mode', choices=["anydoc", "condensed", "condensed-anydoc", "closed-world"], default="closed-world", help="Which mode of scoring to use")
    command_parser.set_defaults(func=do_entity_evaluation)

    command_parser = subparsers.add_parser('mention-evaluation', help='Evaluate a single entry (mention)')
    command_parser.add_argument('-p', '--pred', type=argparse.FileType('r'), required=True, help="A list of predicted entries")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.set_defaults(func=do_mention_evaluation)

    command_parser = subparsers.add_parser('compute-intervals', help='Evaluate P/R/F1 (entity) scores for every entity with 95%% confidence thresholds')
    command_parser.add_argument('-ps', '--preds', type=str, default=(DD+ "/corrected_runs/"), help="A directory with predicted entries")
    command_parser.add_argument('-c', '--confidence', type=float, default=.95, help="Confidence threshold")
    command_parser.add_argument('-s', '--samples', type=int, default=5000, help="Confidence threshold")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.set_defaults(func=do_compute_intervals)

    command_parser = subparsers.add_parser('pooling-bias', help='Evaluate pooling bias')
    command_parser.add_argument('-ps', '--preds', type=str, default=(DD+ "/corrected_runs/"), help="A directory with predicted entries")
    command_parser.add_argument('-m', '--mode', choices=["anydoc", "condensed", "condensed-anydoc", "closed-world"], default="closed-world", help="Which mode of scoring to use")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.set_defaults(func=do_pooling_bias)

    command_parser = subparsers.add_parser('standardized-evaluation', help='Evaluate standardized micro/macro F1 (entity) scores for every entity with 95%% confidence thresholds')
    command_parser.add_argument('-ps', '--preds', type=str, default=(DD+ "/corrected_runs/"), help="A directory with predicted entries")
    command_parser.add_argument('-c', '--confidence', type=float, default=.95, help="Confidence threshold")
    command_parser.add_argument('-s', '--samples', type=int, default=5000, help="Confidence threshold")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Where to write output.")
    command_parser.add_argument('-ov', '--output-vis', type=argparse.FileType('w'), default="vis.tsv", help="Where to write visualization output.")
    command_parser.set_defaults(func=do_standardized_evaluation)

    # TODO: measurement of pairwise significance and diagrams.

    ARGS = parser.parse_args()
    if ARGS.func:
        ARGS.func(ARGS)
    else:
        parser.print_help()
        sys.exit(1)

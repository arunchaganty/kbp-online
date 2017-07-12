#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 2: pooling bias
"""
import pdb
import csv
import sys
from collections import namedtuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import matplotlib.colors as pltc

plt.rc('text', usetex=True)
plt.rc('font', family='serif', size=16)

def teamid(runid):
    return runid[3:-1]

def load_data(fstream):
    reader = csv.reader(fstream, delimiter='\t')
    header = next(reader)
    Row = namedtuple("Row", [h.replace("-", "_") for h in header])
    return [Row(*row) for row in reader]

def read_series(lst, *fields):
    return [np.array(x) for x in zip(*[[float(getattr(row, field)) for field in fields] for row in lst])]

def do_command(args):
    lbls = {
        "pool": "Pooling",
        "simple": "Simple",
        "joint": "Joint",
        "p": "Precision",
        "r": "Recall",
        "f1": "$F_1$",
        }
    markers = {
        "pool": "o",
        "simple": "v",
        "joint": "s",
        }

    colors = {
        "pool":"#9A2617",
        "simple": "#829356",
        "joint": "#093145",
        }

    inputs = {
        "pool": load_data(args.input_pool),
        "simple": load_data(args.input_simple),
        "joint": load_data(args.input_joint),
        }
    outputs = {
        "p": args.output_precision,
        "r": args.output_recall,
        "f1": args.output_f1,
        }

    #run_ids = [row.run_id for row in inputs["pool"]]
    P, R, F1 = read_series(inputs["pool"], "p", "r", "f1") # This is the same for all the series.
    ixs = np.argsort(-F1)[:40] # Remove the worst two systems because they are just too bad.

    # Load data.
    data = {}
    for k, vs in inputs.items():
        data[k] = read_series(vs, "p", "r", "f1", "delta_p", "delta_r", "delta_f1", "p_lrange", "r_lrange", "f1_lrange", "p_rrange", "r_rrange", "f1_rrange")
        # Remove outlier rows.
        data[k] = [X[ixs] for X in data[k]]

    for i, series in enumerate(["p", "r", "f1"]):
        fig, ax = plt.subplots()
        for k in ["pool", "simple", "joint"]:
            X, dX, dX_L, dX_R = [data[k][j] for j in range(i, len(data[k]), 3)] # skip by 3.
            # order input.
            #ixs = np.argsort(-X)
            #X, dX, dX_L, dX_R = X[ixs], dX[ixs], dX_L[ixs], dX_R[ixs]
            # Show in %s
            X, dX, dX_L, dX_R = 100 * X, 100 * dX, 100 * dX_L, 100 * dX_R
            Xs = 1 + np.arange(len(X))

            print("Median confidence interval for {} {} is {:.4f}".format(series, k, np.median(dX_L + dX_R)))

            # dX_L and dX_R are positive relative to dX, undo that weird transformation.
            #pdb.set_trace()
            dX_L = dX - dX_L
            dX_R = dX_R + dX

            # Fit the mean curve, L curve and R curve.
            mean = np.poly1d(np.polyfit(Xs, dX, 1))
            LB = np.poly1d(np.polyfit(Xs, dX_L - dX + mean(Xs), 1)) # shift mean
            UB = np.poly1d(np.polyfit(Xs, dX_R - dX + mean(Xs), 1))
            #dX_L, dX_R = dX_L - dX + mean(Xs), dX_R - dX + mean(Xs)
            dX_L, dX_R = LB(Xs), UB(Xs)

            ax.plot(Xs, -mean(Xs), color=colors[k], label=lbls[k], linestyle='--', zorder=4)

            ax.scatter(Xs, -dX, color=colors[k], marker=markers[k], alpha=0.6, zorder=2) # Faint dots.

            # Plot with errorbars -- this is really hard to see.
            #ax.errorbar(Xs, -dX, yerr=[dX_L, dX_R], linestyle='', capsize=10, color=colors[k], marker=markers[k], alpha=0.9, zorder=2) # Faint dots.
            #ax.errorbar(Xs, -dX, yerr=[LB(Xs), UB(Xs)], linestyle='', capsize=10, color=colors[k], marker=markers[k], alpha=0.9, zorder=2) # Faint dots.
            ax.fill_between(Xs, -dX_L, -dX_R, color=colors[k], alpha=0.2, zorder=1)
            ax.plot(Xs, -dX_L, color=colors[k], linestyle=':', alpha=0.8, zorder=3)
            ax.plot(Xs, -dX_R, color=colors[k], linestyle=':', alpha=0.8, zorder=3)

        # now plot both limits against eachother
        ax.plot(Xs, [0]*len(Xs), 'k-', alpha=0.75, zorder=0)
        ax.set_xlabel("System Rank")
        ax.set_ylabel("{} Bias".format(lbls[series]))
        ax.legend()
        fig.set_tight_layout(True)
        plt.savefig(outputs[series])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Plots a scatter-variance plot for different experiments.')
    parser.add_argument('-ip', '--input-pool', type=argparse.FileType('r'), default='data/simulation/pool.tsv', help="Pooling file.")
    parser.add_argument('-is', '--input-simple', type=argparse.FileType('r'), default='data/simulation/simple.tsv', help="Simple file.")
    parser.add_argument('-ij', '--input-joint', type=argparse.FileType('r'), default='data/simulation/joint.tsv', help="Joint file.")
    parser.add_argument('-op', '--output-precision', type=str, default='simulation/simulation-p.pdf', help="Name of file to output to")
    parser.add_argument('-or', '--output-recall', type=str, default='simulation/simulation-r.pdf', help="Name of file to output to")
    parser.add_argument('-of', '--output-f1', type=str, default='simulation/simulation-f1.pdf', help="Name of file to output to")
    parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 2: pooling bias
"""
import csv
import sys
from collections import namedtuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import matplotlib.colors as pltc

plt.rc('text', usetex=True)
plt.rc('font', family='serif')#, size=18)

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
        "simple": "Simple sampling",
        "joint": "Importance sampling",
        "p": "Precision",
        "r": "Recall",
        "f1": "$F_1$",
        }
    markers = {
        "pool": "o",
        "simple": "v",
        "joint": "s",
        }

    colors = ["#9A2617", "#829356", "#093145"]
    colors = {
        "pool": colors[0],
        "simple": colors[1],
        "joint": colors[2],
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
            ixs = np.argsort(X)
            X, dX, dX_L, dX_R = X[ixs], dX[ixs], dX_L[ixs], dX_R[ixs]

            bound_L, bound_R = np.median(dX_L), np.median(dX_R)

            # Fit the mean curve, L curve and R curve.
            mean = np.poly1d(np.polyfit(X, X-dX, 1))
            LB = np.poly1d(np.polyfit(X, mean(X)-dX_L, 2))
            UB = np.poly1d(np.polyfit(X, mean(X)+dX_R, 2))

            ax.plot(X, mean(X), color=colors[k], label=lbls[k], linestyle='--', zorder=4)
            size = (dX_L + dX_R)/2
            #ax.add_collection(EllipseCollection(widths=size, heights=size, angles=0, units='xy',
            #                                       facecolors=colors[k], alpha=0.3,
            #                                       offsets=list(zip(X, X-dX)), transOffset=ax.transData))
            ax.scatter(X, X - dX, color=colors[k], marker=markers[k], alpha=0.6, zorder=2) # Faint dots.
            #ax.errorbar(X, X - dX, yerr=[dX_L, dX_R], linestyle='', capsize=10, color=colors[k], marker=markers[k], alpha=0.9, zorder=2) # Faint dots.
            ax.fill_between(X, LB(X), UB(X), color=colors[k], alpha=0.2, zorder=1)
            ax.plot(X, UB(X), color=colors[k], linestyle=':', alpha=0.8, zorder=3)
            ax.plot(X, LB(X), color=colors[k], linestyle=':', alpha=0.8, zorder=3)

            #ax.fill_between(X, mean(X)-dX_L, mean(X)+dX_R, color=colors[k], alpha=0.3, zorder=1)
            #ax.plot(X, mean(X)-dX_L, color=colors[k], linestyle=':', alpha=0.8, zorder=3)
            #ax.plot(X, mean(X)+dX_R, color=colors[k], linestyle=':', alpha=0.8, zorder=3)
        lims = [
            np.min([ax.get_xlim(), ax.get_ylim()]),  # min of both axes
            np.max([ax.get_xlim(), ax.get_ylim()]),  # max of both axes
        ]
        # now plot both limits against eachother
        ax.plot(lims, lims, 'k-', alpha=0.75, zorder=0)
        ax.set_xlabel("True {}".format(lbls[series]))
        ax.set_ylabel("Estimated {}".format(lbls[series]))
        ax.set_aspect('equal')
        ax.set_xlim(lims)
        ax.set_ylim(lims)
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

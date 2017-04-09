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

def teamid(runid):
    return runid[3:-1]

def load_data(fstream):
    reader = csv.reader(fstream, delimiter='\t')
    header = next(reader)
    Row = namedtuple("Row", [h.replace("-", "_") for h in header])
    return [Row(*row) for row in reader]

def do_command(args):
    root = load_data(args.root)
    data = load_data(args.input)


    systems = [(float(getattr(r, args.root_metric)), r.system) for r in root if r.system != "LDC"]
    I = {sys: i for i, (_, sys) in enumerate(sorted(systems, reverse=True))}

    X0 = np.zeros(len(systems)) # Original score
    for r in root:
        if r.system == "LDC": continue
        X0[I[r.system]] = float(getattr(r, args.metric))

    X = np.zeros(len(systems)) # Original score
    Y = np.zeros(len(systems)) # New score
    for r in data:
        if r.system == "LDC": continue
        X[I[r.system]] = float(getattr(r, args.metric))
        X[I[r.system]] = float(getattr(r, args.metric))
        Y[I[r.system]] = float(getattr(r, args.metric + "_lto"))

    # Print statistics.
    print("Metric bias: {:.2f}%".format(np.mean(abs(X - X0)) * 100))
    print("Mean bias: {:.2f}%".format(np.mean(abs(X - Y)) * 100))
    print("Median bias: {:.2f}%".format(np.median(abs(X - Y)) * 100))
    print("Mean bias (top 40): {:.2f}%".format(np.mean((abs(X - Y))[:40]) * 100))
    print("Median bias (top 40): {:.2f}%".format(np.median((abs(X - Y))[:40]) * 100))
    print("Mean bias (top 10): {:.2f}%".format(np.mean((abs(X - Y))[:10]) * 100))
    print("Median bias (top 10): {:.2f}%".format(np.median((abs(X - Y))[:10]) * 100))
    print("Mean bias (top 3): {:.2f}%".format(np.mean((abs(X - Y))[:3]) * 100))
    print("Median bias (top 3): {:.2f}%".format(np.median((abs(X - Y))[:3]) * 100))

    # Read data
    rc('text', usetex=True)
    rc('font', family='serif')#, size=22)

    # Set up plotter.
    plt.subplot(2,1,1)
    plt.ylabel('Macro $F_1$', fontsize=22)

    plt.errorbar(np.arange(1,len(systems)+1), X, yerr=[X - Y, X-X], fmt='o', color='k', linestyle='-', capsize=0, alpha=0.7, label="Actual score")
    plt.plot(np.arange(1,len(systems)+1), Y, color='g', marker='^', linestyle='', alpha=0.9, label="Evaluation score")
    plt.legend()

    plt.subplot(2,1,2)
    plt.ylabel(r'$\Delta$ Macro $F_1$', fontsize=22)
    plt.xlabel('Systems', fontsize=22)
    plt.errorbar(np.arange(1,len(systems)+1), X-X, yerr=[X - Y, X-X], fmt='o', color='k', linestyle='-', capsize=0, alpha=0.7)

    plt.savefig(args.output)
    #plt.show()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser( description='' )
    parser.add_argument('-r', '--root', type=argparse.FileType('r'), default='data/pooling_bias_closed-world.tsv', help="The closed world scores file that provides ranking, etc.")
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), default='data/pooling_bias_closed-world.tsv', help="File to plot.")
    parser.add_argument('-m', '--metric', type=str, default='macro_f1', help="")
    parser.add_argument('-mr', '--root-metric', type=str, default='macro_f1', help="Metric to use when sorting the root")
    parser.add_argument('-o', '--output', type=str, default='pooling-bias.pdf', help="Name of file to output to")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

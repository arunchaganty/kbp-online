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
    data_anydoc = load_data(args.input_anydoc)

    systems = [(float(getattr(r, args.root_metric)), r.system) for r in root if r.system != "LDC"]
    I = {sys: i for i, (_, sys) in enumerate(sorted(systems, reverse=True))}

    X0 = np.zeros(len(systems)) # Original score
    for r in root:
        if r.system == "LDC": continue
        X0[I[r.system]] = float(getattr(r, args.metric))

    X = np.zeros(len(systems)) # Original score
    Y = np.zeros(len(systems)) # New score
    X_ = np.zeros(len(systems)) # anydoc score
    Z = np.zeros(len(systems)) # anydoc score
    for r in data:
        if r.system == "LDC": continue
        X[I[r.system]] = float(getattr(r, args.metric))
        Y[I[r.system]] = float(getattr(r, args.metric + "_lto"))
    for r in data_anydoc:
        if r.system == "LDC": continue
        X_[I[r.system]] = float(getattr(r, args.metric))
        Z[I[r.system]] = float(getattr(r, args.metric + "_lto")) - (X_[I[r.system]] - X[I[r.system]])

    # Print statistics.
    print("Metric bias: {:.2f}%  {:.2f}%".format(np.mean(abs(X - X0)) * 100, np.mean(abs(X_ - X0)) * 100))
    print("Mean bias: {:.2f}% {:.2f}%".format(np.mean(abs(X - Y)) * 100, np.mean(abs(X - Z)) * 100))
    print("Median bias: {:.2f}% {:.2f}%".format(np.median(abs(X - Y)) * 100, np.median(abs(X - Z)) * 100))
    print("Mean bias (top 40): {:.2f}% {:.2f}%".format(np.mean((abs(X - Y))[:40]) * 100, np.mean((abs(X - Z))[:40]) * 100))
    print("Median bias (top 40): {:.2f}% {:.2f}%".format(np.median((abs(X - Y))[:40]) * 100, np.median((abs(X - Z))[:40]) * 100))
    print("Mean bias (top 10): {:.2f}% {:.2f}%".format(np.mean((abs(X - Y))[:10]) * 100, np.mean((abs(X - Z))[:10]) * 100))
    print("Median bias (top 10): {:.2f}% {:.2f}%".format(np.median((abs(X - Y))[:10]) * 100, np.median((abs(X - Z))[:10]) * 100))
    print("Mean bias (top 3): {:.2f}% {:.2f}%".format(np.mean((abs(X - Y))[:3]) * 100, np.mean((abs(X - Z))[:3]) * 100))
    print("Median bias (top 3): {:.2f}% {:.2f}%".format(np.median((abs(X - Y))[:3]) * 100, np.median((abs(X - Z))[:3]) * 100))

    # Read data
    rc('text', usetex=True)
    rc('font', family='serif', size=18)

    fig, ax = plt.subplots()
    # Set up plotter.
    #plt.subplot(2,1,1)
    ax.set_ylabel('Macro $F_1$', fontsize=22)
    ax.set_xlabel('Systems', fontsize=22)

    ax.errorbar(np.arange(1,len(systems)+1), X, yerr=[X - Y, X-X], fmt='o', color='k', linestyle='-', capsize=0, alpha=0.7, label="Pooled score")
    ax.plot(np.arange(1,len(systems)+1), Z, color='r', marker='s', linestyle='', alpha=0.9, label="Unpooled anydoc score")
    ax.plot(np.arange(1,len(systems)+1), Y, color='g', marker='^', linestyle='', alpha=0.9, label="Unpooled score")
    legend = ax.legend(fontsize=16)
    legend.set_alpha(0.5)

    fig.set_tight_layout(True)

    #plt.subplot(2,1,2)
    #plt.ylabel(r'Pooling bias', fontsize=22)
    #plt.xlabel('Systems', fontsize=22)
    #plt.ylim((-max(X-Y),0))
    #if max(X-Y) < .04:
    #    plt.yticks([-0.00, -0.01, -0.02, -0.03])
    #plt.errorbar(np.arange(1,len(systems)+1), X-X, yerr=[X - Y, X-X], fmt='o', color='k', linestyle='-', capsize=0, alpha=0.7)

    plt.savefig(args.output)
    #plt.show()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser( description='' )
    parser.add_argument('-r', '--root', type=argparse.FileType('r'), default='data/pooling_bias/pooling_bias_closed-world.tsv', help="The closed world scores file that provides ranking, etc.")
    parser.add_argument('-mr', '--root-metric', type=str, default='macro_f1', help="Metric to use when sorting the root")
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), default='data/pooling_bias/pooling_bias_closed-world.tsv', help="File to plot.")
    parser.add_argument('-a', '--input-anydoc', type=argparse.FileType('r'), default='data/pooling_bias/pooling_bias_anydoc.tsv', help="File to plot.")
    parser.add_argument('-m', '--metric', type=str, default='macro_f1', help="")
    parser.add_argument('-o', '--output', type=str, default='pooling-bias.pdf', help="Name of file to output to")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

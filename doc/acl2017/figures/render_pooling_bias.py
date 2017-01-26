#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 2: pooling bias
"""

import csv
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
from collections import defaultdict

def do_command(args):
    reader = csv.reader(args.input, delimiter='\t')
    header = next(reader)

    a = '-anydoc' if args.anydoc else ""

    I = {n: i-1 for i, n in enumerate(header)}

    data = np.array([[float(x) for x in row[1:]] for row in reader if row[0] != "LDC"])

    # Read data
    rc('text', usetex=True)
    rc('font', family='serif')#, size=22)

    # Set up plotter.
    plt.ylabel('Macro $F_1$', fontsize=22)
    plt.xlabel('Systems', fontsize=22)


    ixs = (-data).argsort(0).T[I[args.metric+a]]
    data = data[ixs, :]

    p, loo, lto = data.T[I[args.metric+a]], data.T[I[args.metric+'-loo'+a]], data.T[I[args.metric+'-lto'+a]]

    plt.errorbar(np.arange(1,data.shape[0]+1), p, yerr=[p - lto, p - p], fmt='o', color='k', linestyle='-', capsize=0, alpha=0.7, label="Pooled score")
    plt.plot(np.arange(1,data.shape[0]+1), lto, color='g', marker='^', linestyle='', alpha=0.9, label="Leave-team-out pooling bias")
    plt.plot(np.arange(1,data.shape[0]+1), loo, color='b', marker='d', linestyle='', alpha=0.9, label="Leave-one-out pooling bias")
    plt.legend()

    plt.savefig(args.output)
    #plt.show()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser( description='' )
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=sys.stdin, help="")
    parser.add_argument('-m', '--metric', type=str, default='macro-f1', help="")
    parser.add_argument('-a', '--anydoc', action='store_true', default=False, help="")
    parser.add_argument('-o', '--output', type=str, default='pooling-bias.pdf', help="")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

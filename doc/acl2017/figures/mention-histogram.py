#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""

"""

import csv
import sys

import matplotlib.pyplot as plt
from matplotlib import rc
from collections import defaultdict

def do_command(args):
    # Read data
    rc('text', usetex=True)
    #rc('font', size=22)

    data = defaultdict(list)
    for value, unit in csv.reader(args.input, delimiter='\t'):
        data[unit].append(float(value))

    # Set up plotter.
    plt.ylabel('Number of mentions', fontsize=22)
    plt.xlabel('Mention value', fontsize=22)
    plt.xscale('log')
    bins = [10**i for i in range(-2,11)]

    plt.hist(data.values(), bins, stacked=True, label=data.keys())
    plt.legend()

    plt.savefig(args.output)
    #plt.show()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser( description='' )
    parser.add_argument('--input', type=argparse.FileType('r'), default=sys.stdin, help="")
    parser.add_argument('--output', type=str, default='mention-histogram.pdf', help="")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

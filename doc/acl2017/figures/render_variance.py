#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 3: pooling bias
"""

import csv
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
from collections import Counter

def do_command(args):
    n = args.doc_ratio
    N = 10
    R = np.linspace(0, 1, N+1)
    Y = np.linspace(0, 1, N+1)

    grid = np.zeros((N+1,N+1))
    for i, r in enumerate(R):
        for j, y in enumerate(Y):
            grid[i,j] = 1 + (1 - r*y)/((1-y)/n + (1-r)) if (r < 1. or y < 1.) else 1+n

    fig, ax = plt.subplots()
    cax = ax.imshow(grid, origin='lower', interpolation='None', extent=[0, 1, 0, 1], cmap='viridis')

    # TODO: fix alignment bug
    #for i, r in enumerate(R):
    #    for j, y in enumerate(Y):
    #        ax.text(y + .5/(N+1), r + .5/(N+1), '%.1f' % grid[i, j],
    #                 horizontalalignment='center',
    #                 verticalalignment='center',
    #                 )

    # Move left and bottom spines outward by 10 points
    ax.spines['left'].set_position(('outward', 10))
    ax.spines['bottom'].set_position(('outward', 10))
    # Hide the right and top spines
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    # Only show ticks on the left and bottom spines
    ax.yaxis.set_ticks_position('left')
    ax.xaxis.set_ticks_position('bottom')

    cbar = fig.colorbar(cax)
    plt.xlabel("Recall measured on pool")
    plt.ylabel("Recall of the pool")



    plt.savefig(args.output)
    #plt.show()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-r', '--doc-ratio', type=float, default=1., help="ratio of pooled documents to exhaustive documents")
    parser.add_argument('-o', '--output', type=str, default="pool-ratio.pdf", help="")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

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

def do_pool(args):
    d = args.doc_ratio
    N = 20
    R = np.linspace(0.1, 1, N+1)
    Y = np.linspace(0.1, 1, N+1)

    grid = np.zeros((N+1,N+1))
    for i, r in enumerate(R):
        for j, y in enumerate(Y):
            x = r * y
            if r == 0. and y == 0.:
                grid[i,j] = 0
            elif x == 1.:
                grid[i,j] = d
            else:
                v = (1-x)/(y * (1-r) + r * (1-y) / d)
                grid[i,j] = v

    fig, ax = plt.subplots()
    cax = ax.imshow(grid, origin='lower', interpolation='None', extent=[0.1, 1, 0.1, 1], cmap='viridis')

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

def do_unassessed(args):
    d_p = args.doc_pool_ratio
    d_u = args.doc_unassessed_ratio
    p = args.average_precision
    N = 20
    R = np.linspace(0.1, 1, N+1)
    Y = np.linspace(0.1, 1, N+1)

    grid = np.zeros((N+1,N+1))
    for i, r in enumerate(R):
        for j, y in enumerate(Y):
            x = r * p * y 
            if x == 1.:
                grid[i,j] = d
            else:
                v = (1-x)/(p * y * (1-r) + 4 * p * (1-y) * r /(d_p) + 9 * (1-p) * y * r / (d_u))
                grid[i,j] = v

    fig, ax = plt.subplots()
    cax = ax.imshow(grid, origin='lower', interpolation='None', extent=[0.1, 1, 0.1, 1], cmap='viridis')

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

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('pool', help='' )
    command_parser.add_argument('-d', '--doc-ratio', type=float, default=1., help="ratio of pooled documents to exhaustive documents")
    command_parser.add_argument('-o', '--output', type=str, default="variance-ratio-pool.pdf", help="")
    command_parser.set_defaults(func=do_pool)

    command_parser = subparsers.add_parser('unassessed', help='' )
    command_parser.add_argument('-dp', '--doc-pool-ratio', type=float, default=1., help="ratio of pooled documents to exhaustive documents")
    command_parser.add_argument('-du', '--doc-unassessed-ratio', type=float, default=10., help="ratio of pooled documents to exhaustive documents")
    command_parser.add_argument('-p', '--average-precision', type=float, default=0.3, help="average precision of pool")
    command_parser.add_argument('-o', '--output', type=str, default="variance-ratio-unassessed.pdf", help="")
    command_parser.set_defaults(func=do_unassessed)

    ARGS = parser.parse_args()
    if ARGS.func:
        ARGS.func(ARGS)
    else:
        parser.print_help()
        sys.exit(1)

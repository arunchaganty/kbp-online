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
    """
    Data format is really simple, just space separated
    """
    ret = []
    for line in fstream:
        ret.append(list(map(int, line.split())))
    return np.array(ret)

def do_command(args):
    lbls = {
        "simple": "Simple",
        "joint": "Joint",
        "x": "Number of systems",
        "y": r"Number of samples $\times$ 500",
        }
    markers = {
        "simple": "v",
        "joint": "s",
        }

    colors = {
        "simple": "#829356",
        "joint": "#093145",
        "fit":"#9A2617",
        }

    inputs = {
        "simple": load_data(args.input_simple),
        "joint": load_data(args.input_joint),
        }

    output = args.output

    fig, ax = plt.subplots()
    for k in ["simple", "joint"]:
        Y = np.mean(inputs[k], axis=0) / 500
        X = np.arange(len(Y)) + 1

        for trajectory in inputs[k]:
            plt.plot(X, trajectory / 500, color=colors[k], alpha=0.2, zorder=1)
        plt.plot(X, Y, linestyle='-', color=colors[k], marker=markers[k], label=lbls[k], zorder=2)

    coefs, residual, _, _, _ = np.polyfit(Y, X, 2, full=True)
    print(coefs)
    print(residual)

    f = np.poly1d(coefs)
    plt.plot(f(np.arange(Y.max() + 5)), np.arange(Y.max() + 5), color=colors['fit'], linestyle='--', zorder=3, label="$x = {:.1f} + {:.1f} y + {:.1f} y^2$".format(*coefs))

    ax.set_xlim((1, X.max()+10))
    ax.set_ylim((1, Y.max()+1))
    ax.set_xlabel(lbls['x'])
    ax.set_ylabel(lbls['y'])
    ax.legend()
    fig.set_tight_layout(True)
    plt.savefig(output)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Plots a graph of sample trajectories.')
    parser.add_argument('-is', '--input-simple', type=argparse.FileType('r'), default='data/simulation/n_simple_trajectory.txt', help="Simple file.")
    parser.add_argument('-ij', '--input-joint', type=argparse.FileType('r'), default='data/simulation/n_joint_trajectory.txt', help="Joint file.")
    parser.add_argument('-o', '--output', type=str, default='simulation/simulation-n.pdf', help="Name of file to output to")
    parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

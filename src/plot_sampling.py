#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

import json
from collections import namedtuple, Counter

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as pltc
import matplotlib.patches as pltp

plt.rc('text', usetex=True)
plt.rc('font', family='serif')

from kbpo.defs import CANONICAL_RELATIONS, ALL_RELATIONS

# Consider stacked histogram?
def do_plot_entity_histogram(args):
    # First load the data.
    objs = [json.load(fstream) for fstream in args.input]

    # project data onto axis.
    xlabels = []
    ylabels = ["Low frequency", "Medium freq.", "High freq."]
    Y = []
    for obj in objs:
        freq = obj["instance_frequency"]
        xlabels.append(obj['mode'])
        Y.append([freq["low"], freq["med"], freq["high"],])
    Y = np.array(Y).T
    colors = [pltc.to_hex(tuple(plt.cm.viridis.colors[int(i/len(ylabels) * 256)])) for i in range(len(ylabels))]

    inds = np.arange(len(xlabels))
    width = 0.5

    plt.ylabel("Number of entites")
    plt.xlabel("Sampling scheme")
    plt.xticks(inds + width/2, xlabels)

    Y_ = np.zeros(Y.shape[1]) # Remember, rows are now features, columns are systems
    for i, lbl in enumerate(ylabels):
        plt.bar(left=inds, bottom=Y_, height=Y[i], width=width, align='edge', label=ylabels[i], color=colors[i], alpha=0.8)
        Y_ += Y[i]
    plt.legend(bbox_to_anchor=(1.0, .9), bbox_transform=plt.gcf().transFigure, loc="upper right")
    #plt.legend()

    plt.tight_layout(rect=(0,0,0.8,1))
    plt.savefig(args.output)

def do_plot_pair_diagram(args):
    # First load the data.
    obj = json.load(args.input)

    # project data onto axis.
    X = ["Low", "Medium", "High"]
    Y = ["Low", "Medium", "High"]
    Z = [[obj["pair_frequency"]["{} {}".format(l, l_)] for l in ["low", "med", "high"]] for l_ in ["low", "med", "high"]]

    inds = np.arange(len(X))

    plt.matshow(Z, cmap="viridis")
    plt.ylabel("Subject entity")
    plt.xlabel("Object entity")
    plt.xticks(inds, X)
    plt.yticks(inds, Y)
    plt.colorbar()
    plt.savefig(args.output)

# Consider stacked histogram?
def do_plot_relation_histogram(args):
    # First load the data.
    objs = [json.load(fstream) for fstream in args.input]

    # project data onto axis.
    X = CANONICAL_RELATIONS
    Y = []

    xlabels = [r.replace("_", r"\_") for r in CANONICAL_RELATIONS]
    ylabels = []
    for obj in objs:
        freq = obj["relation_frequency"]
        ylabels.append(obj['mode'])
        Y.append([freq.get(r, 0) for r in CANONICAL_RELATIONS])
    colors = [pltc.to_hex(tuple(plt.cm.viridis.colors[int(i/len(ylabels) * 256)])) for i in range(len(ylabels))]

    inds = np.arange(len(X))
    width = .8/len(objs)

    ax = plt.gca()

    ax.set_ylabel("# of instances")
    ax.set_yscale("log")
    ax.set_xlabel("Relation")
    ax.set_xticks(np.arange(len(X)))
    ax.set_xticklabels(xlabels, rotation=45, rotation_mode="anchor", ha="right")

    for i, ylbl in enumerate(ylabels):
        ax.bar(left=inds + i * width, height=Y[i], width=width, align='edge', label=ylbl, color=colors[i], alpha=0.8)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.output)

# Consider stacked histogram?
def do_plot_clusters(args):
    # First load the data.
    objs = [json.load(fstream) for fstream in args.input]

    #fig, axs = plt.subplots(1, 3, sharey=True)
    ax = plt.gca()

    # project data onto axis.
    xlabels = []
    ylabels = ["Low", "Medium", "High"]
    max_cluster_size = 5

    Ys = []
    for obj in objs:
        num_samples = obj.get("num_samples", 10)
        freq = obj["cluster_frequency"]
        xlabels.append(obj['mode'])

        Y = []
        for i, rng in enumerate(["low", "med", "high"]):
            cntr = Counter(min(x, max_cluster_size) for x in freq[rng])
            Y.append([cntr[i]/num_samples for i in range(1, max_cluster_size + 1)])
        Ys.append(np.array(Y))
    colors = [[i / len(xlabels) + j / (len(xlabels) * len(ylabels)) for j in range(len(ylabels))] for i in range(len(xlabels))]
    colors = [[pltc.to_hex(plt.cm.viridis.colors[int(v * 256)]) for v in vs] for vs in colors]
        
    inds = np.arange(max_cluster_size)
    width = 0.8 / len(Ys)
    plt.xticks(inds + 0.4, inds+1)

    for i, (Y, xlabel) in enumerate(zip(Ys, xlabels)):
        Y_ = np.zeros(Y.shape[1])
        for j, ylbl in enumerate(ylabels):
            plt.bar(left=inds + i * width, bottom=Y_, height=Y[j], width=width, align='edge', color=colors[i][j], alpha=0.8)
            Y_ += Y[j]
    plt.legend(handles=[pltp.Patch(facecolor=colors[i][1]) for i in range(len(xlabels))], labels=xlabels, loc="upper right", )
    plt.xlabel("Cluster size")
    plt.ylabel("Number of clusters")
    plt.savefig(args.output)


# TODO make reasonable.
def do_plot_distribution(args):
    # First load the data.
    counts = load_counts(args.counts)
    objs = [json.load(fstream) for fstream in args.input]

    # Identify low, medium, high splits.
    high_max  = sorted(counts.values())[-3]
    low_max, med_max = 3, np.power(high_max, 2./3.)
    low_max, med_max = int(np.ceil(low_max)), int(np.ceil(med_max))

    print(low_max, med_max, high_max)

    # Start by plotting the distribution curve.
    coarse_bins = np.array([1, low_max, med_max, high_max])
    bins = np.exp(np.hstack([
        np.linspace(0, np.log(low_max), 3, endpoint=False),
        np.linspace(np.log(low_max), np.log(med_max), 30, endpoint=False),
        np.linspace(np.log(med_max), np.log(high_max), 20, endpoint=True),
        ]))
    y, x_ = np.histogram(list(counts.values()), bins)
    # x is actually in the midpoint of each x_
    x = (x_[:-1] + x_[1:])/2
    x, y = x[y > 0], y[y > 0]

    # project data onto axis.
    data = {}
    for obj in objs:
        dist = []
        for sample in obj['frequencies']:
            dist_, _ = np.histogram(sample, bins=coarse_bins)
            dist.append(dist_)
        dist = np.array(dist).mean(axis=0)
        dist = normalize_probs(dist)
        # TODO: error bars
        data[obj['mode']] = dist

    fig, ax1 = plt.subplots()

    ax1.set_xscale("log")
    ax1.set_xlabel("# documents with entity")
    ax1.set_yscale("log")
    ax1.set_ylabel("# of entities")
    ax1.set_xlim(1, high_max)

    ax1.axvline(x=low_max, linestyle='--')
    ax1.axvline(x=med_max, linestyle='--')
    ax1.plot(x, y, marker='', linestyle='-')

    ax2 = ax1.twinx()
    ax2.set_ylim(0,1)

    inds = coarse_bins[:-1]
    widths = (coarse_bins[1:] - coarse_bins[:-1])/len(data)

    print(inds)
    print(widths)

    for i, (k, vs) in enumerate(sorted(data.items())):
        ret = ax2.bar(left=inds + i * widths, height=vs, width=widths, align='edge', label=k, alpha=0.4)
        print(ret)

    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)


    fig.savefig(args.output)

# TODO: make reasonable.
def do_plot_cross_distribution(args):
    # First load the data.
    counts = load_counts(args.counts)
    objs = [json.load(fstream) for fstream in args.input]

    # Identify low, medium, high splits.
    high_max  = sorted(counts.values())[-3]
    low_max, med_max = 3, np.power(high_max, 2./3.)
    low_max, med_max = int(np.ceil(low_max)), int(np.ceil(med_max))

    print(low_max, med_max, high_max)

    # Start by plotting the distribution curve.
    coarse_bins = np.array([1, low_max, med_max, high_max])
    bins = [1, 2, 3, 4, 10, 20, 30]

    # Project data onto these bins.
    lows, meds, highs = {}, {}, {}
    for obj in objs:
        low_dist, med_dist, high_dist = [], [], []
        for sample in obj['crosslinks']:
            low, med, high = [], [], []
            for freq, doc_count in sample:
                if freq < low_max:
                    low.append(doc_count)
                elif freq < med_max:
                    med.append(doc_count)
                else:
                    high.append(doc_count)
            low_dist.append(np.histogram(low, bins)[0])
            med_dist.append(np.histogram(med, bins)[0])
            high_dist.append(np.histogram(high, bins)[0])
        low_dist = np.array(low_dist).mean(axis=0)
        med_dist = np.array(med_dist).mean(axis=0)
        high_dist = np.array(high_dist).mean(axis=0)

        # TODO: error bars
        lows[obj['mode']] = low_dist
        meds[obj['mode']] = med_dist
        highs[obj['mode']] = high_dist

    inds = np.arange(0, len(bins)-1)
    width = 1. / len(objs)

    f, axs = plt.subplots(3, sharey=True)

    for ax, dist in zip(axs, [lows, meds, highs]):
        ax.set_yscale("log")
        ax.set_xlabel("# documents with entity")
        ax.set_ylabel("# of entities")

        for i, (label, data) in enumerate(sorted(dist.items())):
            print(len(data))
            ax.bar(left=inds + i * width, height=data, width=width, align='edge', label=label, alpha=0.4)

    f.savefig(args.output)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')

    subparsers = parser.add_subparsers()

    command_parser = subparsers.add_parser('entity', help='Make entity histogram plot')
    command_parser.add_argument('input', type=argparse.FileType('r'), nargs='+', help="JSON files to plot with.")
    command_parser.add_argument('-o', '--output', type=str, default="histogram.pdf", help="Where to output plot file.")
    command_parser.set_defaults(func=do_plot_entity_histogram)

    command_parser = subparsers.add_parser('pairs', help='Make pair histogram plot')
    command_parser.add_argument('input', type=argparse.FileType('r'), help="JSON files to plot with.")
    command_parser.add_argument('-o', '--output', type=str, default="pair.pdf", help="Where to output plot file.")
    command_parser.set_defaults(func=do_plot_pair_diagram)

    command_parser = subparsers.add_parser('relations', help='Make relation histogram plot')
    command_parser.add_argument('input', type=argparse.FileType('r'), nargs='+', help="JSON files to plot with.")
    command_parser.add_argument('-o', '--output', type=str, default="histogram.pdf", help="Where to output plot file.")
    command_parser.set_defaults(func=do_plot_relation_histogram)

    command_parser = subparsers.add_parser('clusters', help='Make pair histogram plot')
    command_parser.add_argument('input', type=argparse.FileType('r'), nargs='+', help="JSON files to plot with.")
    command_parser.add_argument('-o', '--output', type=str, default="pair.pdf", help="Where to output plot file.")
    command_parser.set_defaults(func=do_plot_clusters)

    command_parser = subparsers.add_parser('plot-distribution', help='Make plots')
    command_parser.add_argument('input', type=argparse.FileType('r'), nargs='+', help="JSON files to plot with.")
    command_parser.add_argument('-o', '--output', type=str, default="distribution.png", help="Where to output plot file.")
    command_parser.set_defaults(func=do_plot_distribution)

    command_parser = subparsers.add_parser('plot-cross-distribution', help='Make plots')
    command_parser.add_argument('input', type=argparse.FileType('r'), nargs='+', help="JSON files to plot with.")
    command_parser.add_argument('-o', '--output', type=str, default="cross_distribution.png", help="Where to output plot file.")
    command_parser.set_defaults(func=do_plot_cross_distribution)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

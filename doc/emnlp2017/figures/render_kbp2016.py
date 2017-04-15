#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot KBP 2016 experiments.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#KBP 2016 official scores
#System 1 - Patterns
#System 2 - Patterns+Sup
#System 3 - Patterns+Sup+RNN
official_scores = {
        'p': [0.3962, 0.3697, 0.2226], 
        'r': [0.0739, 0.1549, 0.2500], 
        'f1':[0.1246, 0.2184, 0.2355], 
        }
def do_command(args):
    colors = ["#9A2617", "#829356", "#093145"]
    colors = {
        "official": colors[0],
        "simple": colors[1],
        "joint": colors[2],
        }


    simple = pd.read_csv(ARGS.input_simple, delimiter='\t')
    joint = pd.read_csv(ARGS.input_joint, delimiter='\t')

    width=0.2

    def autolabel(ax, rects):
        """
        Attach a text label above each bar displaying its height
        """
        return
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + 1.1*rect.get_width()/2., height + .06*ax.get_ylim()[1],
                    "{0:.2f}".format(height), 
                    ha='center', va='bottom')
    ind = 0.1+np.arange(sum(simple['run_id'].str.contains(ARGS.sampling_scheme)))

    #Latex code
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif', size=16)

    #Precision plot
    simple_filtered = simple[simple['run_id'].str.contains(ARGS.sampling_scheme)]
    joint_filtered = joint[simple['run_id'].str.contains(ARGS.sampling_scheme)]
    fig, ax = plt.subplots()
    rects1 = ax.bar(ind, simple_filtered['p'], width, color=colors['simple'], yerr=(simple_filtered['err-p-left']+simple_filtered['err-p-right'])/2, capsize = 5, ecolor='black')
    rects2 = ax.bar(ind+width, joint_filtered['p'], width, color=colors['joint'], yerr=(joint_filtered['err-p-left']+joint_filtered['err-p-right'])/2, capsize = 5, ecolor='black')
    rects3 = ax.bar(ind+2*width, official_scores['p'], width, color=colors['official'])
    ax.set_ylabel('Precision')
    #ax.set_title('Precision for systems under evaluation schemes')
    ax.set_xticks(ind + width)
    ax.set_xticklabels(('Patterns', 'Supervised', 'RNN'))

    ax.legend((rects1[0], rects2[0], rects3[0]), ('Simple', 'Joint', 'Official'))


    autolabel(ax, rects1)
    autolabel(ax, rects2)
    fig.set_tight_layout(True)
    plt.savefig('kbp2016/kbp2016_precision.pdf', bbox_inches = 'tight')

    #Recall plot
    simple_filtered = simple[simple['run_id'].str.contains(ARGS.sampling_scheme)]
    joint_filtered = joint[simple['run_id'].str.contains(ARGS.sampling_scheme)]
    fig, ax = plt.subplots()
    rects1 = ax.bar(ind, simple_filtered['r'], width, color="#004949", yerr=(simple_filtered['err-r-left']+simple_filtered['err-r-right'])/2, capsize = 5, ecolor='black')
    rects2 = ax.bar(ind+width, joint_filtered['r'], width, color="#006DDB", yerr=(joint_filtered['err-r-left']+joint_filtered['err-r-right'])/2, capsize = 5, ecolor='black')
    rects3 = ax.bar(ind+2*width, official_scores['r'], width, color=colors['official'])
    ax.set_ylabel('Recall')
    #ax.set_title('Recall for systems under evaluation schemes')
    ax.set_xticks(ind + width)
    ax.set_xticklabels(('Patterns', 'Supervised', 'RNN'))

    ax.legend((rects1[0], rects2[0], rects3[0]), ('Simple', 'Joint', 'Official'))
    autolabel(ax, rects1)
    autolabel(ax, rects2)
    fig.set_tight_layout(True)
    plt.savefig('kbp2016/kbp2016_recall.pdf', bbox_inches = 'tight')

    #F1 plot
    simple_filtered = simple[simple['run_id'].str.contains(ARGS.sampling_scheme)]
    joint_filtered = joint[simple['run_id'].str.contains(ARGS.sampling_scheme)]
    fig, ax = plt.subplots()
    rects1 = ax.bar(ind, simple_filtered['f1'], width, color=colors['simple'], yerr=(simple_filtered['err-f1-left']+simple_filtered['err-f1-right'])/2, capsize = 5, ecolor='black')
    rects2 = ax.bar(ind+width, joint_filtered['f1'], width, color=colors['joint'], yerr=(joint_filtered['err-f1-left']+joint_filtered['err-f1-right'])/2, capsize = 5, ecolor='black')
    #rects3 = ax.bar(ind+2*width, official_scores['f1'], width, color=colors['official'])
    ax.set_ylabel('F1')
    #ax.set_title('Recall for systems under evaluation schemes')
    ax.set_xticks(ind + width)
    ax.set_xticklabels(('Rule-based', 'Logistic Classifier', 'Neural Network'))

    #ax.legend((rects1[0], rects2[0], rects3[0]), ('Simple', 'Joint', 'Official'))
    ax.legend((rects1[0], rects2[0]), ('Simple', 'Joint'))
    autolabel(ax, rects1)
    autolabel(ax, rects2)
    fig.set_tight_layout(True)
    plt.savefig('kbp2016/kbp2016_f1.pdf', bbox_inches = 'tight')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Plot histograms comparing different scores on KBP 2016')
    parser.add_argument('-is', '--input-simple', type=argparse.FileType('r'), default='data/kbp2016/kbp2016_simple.tsv', help="Simple evaluation.")
    parser.add_argument('-ij', '--input-joint', type=argparse.FileType('r'), default='data/kbp2016/kbp2016_joint.tsv', help="Joint evaluation.")
    parser.add_argument('-s', '--sampling-scheme', type=str, default='relation', help="Sampling scheme to plot, entity or relation")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

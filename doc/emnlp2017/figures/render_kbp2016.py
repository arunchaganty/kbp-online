import pandas as pd
import argparse
import numpy as np
import matplotlib.pyplot as plt
parser = argparse.ArgumentParser(description='Plots results on kbp-2016 dataset for different experiments.')
parser.add_argument('-is', '--input-simple', type=argparse.FileType('r'), default='data/kbp2016/kbp2016_simple.tsv', help="Simple evaluation.")
parser.add_argument('-ij', '--input-joint', type=argparse.FileType('r'), default='data/kbp2016/kbp2016_joint.tsv', help="Joint evaluation.")
parser.add_argument('-s', '--sampling-scheme', type=str, default='relation', help="Sampling scheme to plot, entity or relation")

#parser.add_argument('-io', '--input-official', type=argparse.FileType('r'), default='data/kbp2016/kbp2016_joint.tsv', help="Pooling evaluation.")

ARGS = parser.parse_args()
simple = pd.read_csv(ARGS.input_simple, delimiter='\t')
joint = pd.read_csv(ARGS.input_joint, delimiter='\t')

width=0.2

def autolabel(ax, rects):
    """
    Attach a text label above each bar displaying its height
    """
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + 1.1*rect.get_width()/2., height + .03*ax.get_ylim()[1],
                "{0:.2f}".format(height), 
                ha='center', va='bottom')
ind = 0.1+np.arange(sum(simple['run_id'].str.contains(ARGS.sampling_scheme)))

#Latex code
plt.rc('text', usetex=True)
plt.rc('font', family='serif')#, size=18)

#Precision plot
simple_filtered = simple[simple['run_id'].str.contains(ARGS.sampling_scheme)]
joint_filtered = joint[simple['run_id'].str.contains(ARGS.sampling_scheme)]
fig, ax = plt.subplots()
rects1 = ax.bar(ind, simple_filtered['p'], width, color="#004949", yerr=(simple_filtered['err-p-left']+simple_filtered['err-p-right'])/2, capsize = 5, ecolor='black')
rects2 = ax.bar(ind+width, joint_filtered['p'], width, color="#006DDB", yerr=(joint_filtered['err-p-left']+joint_filtered['err-p-right'])/2, capsize = 5, ecolor='black')
ax.set_ylabel('Precision')
ax.set_title('Precision for systems under evaluation schemes')
ax.set_xticks(ind + width)
ax.set_xticklabels(('Patterns', 'Supervised', 'RNN'))

ax.legend((rects1[0], rects2[0]), ('simple', 'joint'), loc='lower right')


autolabel(ax, rects1)
autolabel(ax, rects2)
fig.set_tight_layout(True)
plt.savefig('kbp2016_precision.pdf', bbox_inches = 'tight')

#Recall plot
simple_filtered = simple[simple['run_id'].str.contains(ARGS.sampling_scheme)]
joint_filtered = joint[simple['run_id'].str.contains(ARGS.sampling_scheme)]
fig, ax = plt.subplots()
rects1 = ax.bar(ind, simple_filtered['r'], width, color="#004949", yerr=(simple_filtered['err-r-left']+simple_filtered['err-r-right'])/2, capsize = 5, ecolor='black')
rects2 = ax.bar(ind+width, joint_filtered['r'], width, color="#006DDB", yerr=(joint_filtered['err-r-left']+joint_filtered['err-r-right'])/2, capsize = 5, ecolor='black')
ax.set_ylabel('Recall')
ax.set_title('Recall for systems under evaluation schemes')
ax.set_xticks(ind + width)
ax.set_xticklabels(('Patterns', 'Supervised', 'RNN'))

ax.legend((rects1[0], rects2[0]), ('simple', 'joint'), loc='lower right')
autolabel(ax, rects1)
autolabel(ax, rects2)
fig.set_tight_layout(True)
plt.savefig('kbp2016_recall.pdf', bbox_inches = 'tight')




import boto
from boto.mturk.connection import MTurkConnection
from boto.mturk.question  import ExternalQuestion
from connection import connect
import urllib
import argparse
import ConfigParser
import sys, os
import time
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('metadata_file', nargs=1, type=argparse.FileType('r'), default=sys.stdin, help="File or stdin containing documents paths")
parser.add_argument('config_file', type=str, help="Config file containing parameters to spin the batch")
args = parser.parse_args()
config = ConfigParser.ConfigParser()
config.read(args.config_file)
mtc = connect(config.get('default', 'target'))
answer_field = config.get('default', 'answer_field')
metadata = pd.read_csv(args.metadata_file[0], sep='\t')
batchname = args.metadata_file[0].name.split('/')[-1]
answers = []
for idx, row in metadata.iterrows():
    HITId = row['HITId']
    assignments = mtc.get_assignments(HITId)
    units = -1 if not 'length' in row else row['length']
    reward = -1 if not 'reward' in row else row['reward']
    for assignment in assignments:
        print dir(assignment)
        worker_id = assignment.WorkerId
        worker_answer = ''
        doc_id = ''
        comment = ''
        timeTaken = ''
        for answer in assignment.answers[0]:
            #print answer.qid
            if answer.qid == answer_field:
                worker_answer = answer.fields[0]
            if answer.qid == 'docId':
                doc_id = answer.fields[0]
            if answer.qid == 'comment':
                comment = answer.fields[0]
            if answer.qid == 'td':
                timeTaken = answer.fields[0]
#                print u"The Worker with ID {} for HITId {} gave the answer {}".format(worker_id, HITId, worker_answer)
        print assignment.AssignmentId, doc_id, timeTaken, comment
        answers.append({'workerId': worker_id, 'assignmentId': assignment.AssignmentId, 'HITId': HITId, answer_field: worker_answer, 'doc_id': doc_id, 'comments': comment, 'timeTaken': timeTaken, 'units': units, 'reward': reward})

#print answers
answers_dir = './answers/'
if not os.path.exists(answers_dir):
    os.makedirs(answers_dir) 
answers_filepath = answers_dir+batchname
pd.DataFrame(answers).to_csv(path_or_buf = answers_filepath, sep = '\t', index=False, 
        columns=['doc_id', 'HITId', 'workerId','assignmentId', 'timeTaken', 'units', 'reward', 'comments', answer_field, ],
        encoding='utf-8')


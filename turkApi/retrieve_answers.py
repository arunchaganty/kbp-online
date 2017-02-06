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
answers = []
for HITId in metadata['HITId']:
    assignments = mtc.get_assignments(HITId)
    for assignment in assignments:
        print dir(assignment)
        worker_id = assignment.WorkerId
        worker_answer = '10'
        doc_id = ''
        comment = ''
        for answer in assignment.answers[0]:
            print answer.qid
            if answer.qid == answer_field:
                worker_answer = answer.fields[0]
            if answer.qid == 'docId':
                doc_id = answer.fields[0]
            if answer.qid == 'comment':
                comment = answer.fields[0]
#                print u"The Worker with ID {} for HITId {} gave the answer {}".format(worker_id, HITId, worker_answer)
        answers.append({'workerId': worker_id, 'assignmentId': assignment.AssignmentId, 'HITId': HITId, answer_field: worker_answer, 'doc_id': doc_id, 'comments': comment})

print answers
answers_dir = './answers/'
if not os.path.exists(answers_dir):
    os.makedirs(answers_dir) 
timestr = time.strftime("%Y%m%d-%H%M%S")
answers_filepath = answers_dir+args.config_file.split('/')[-1]+'.'+timestr+'.csv'
pd.DataFrame(answers).to_csv(path_or_buf = answers_filepath, sep = '\t', index=False, 
        columns=['doc_id', 'HITId', 'workerId','assignmentId', 'comments', answer_field],
        encoding='utf-8')


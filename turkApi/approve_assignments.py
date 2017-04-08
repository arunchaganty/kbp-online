import boto
from boto.mturk.connection import MTurkConnection, MTurkRequestError
from boto.mturk.question  import ExternalQuestion
from connection import connect
import urllib
import argparse
import ConfigParser
import sys, os
import time
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('answers_file', nargs=1, type=argparse.FileType('r'), default=sys.stdin, help="File or stdin containing documents paths")
parser.add_argument('config_file', type=str, help="Config file containing parameters to spin the batch")
args = parser.parse_args()
config = ConfigParser.ConfigParser()
config.read(args.config_file)
mtc = connect(config.get('default', 'target'))
answers_file = pd.read_csv(args.answers_file[0], sep='\t')
batchname = args.answers_file[0].name.split('/')[-1]
approved = []
for assignmentId in answers_file['assignmentId']:
    try: 
        x = mtc.approve_assignment(assignmentId)
        print "Approved", assignmentId
        approved.append({'assignmentId': assignmentId, 'response': x})
    except MTurkRequestError as err:
        print err

approved_dir = './approved/'
if not os.path.exists(approved_dir):
    os.makedirs(approved_dir) 
approved_filepath = approved_dir+batchname
pd.DataFrame(approved).to_csv(path_or_buf = approved_filepath, sep = '\t', index=False, 
        columns=['assignmentId', 'response'],
        encoding='utf-8')



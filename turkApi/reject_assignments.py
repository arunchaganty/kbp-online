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
parser.add_argument('answers_file', nargs=1, type=argparse.FileType('r'), default=sys.stdin, help="File or stdin containing documents paths")
parser.add_argument('config_file', type=str, help="Config file containing parameters to spin the batch")
args = parser.parse_args()
config = ConfigParser.ConfigParser()
config.read(args.config_file)
mtc = connect(config.get('default', 'target'))
answers_file = pd.read_csv(args.answers_file[0], sep='\t')
for assignmentId, answer in zip(answers_file['assignmentId'], answers_file[config.get('default', 'answer_field')]):
    while True:
        try:
            # Note: Python 2.x users should use raw_input, the equivalent of 3.x's input
            print "Answer: ", answer
            response = raw_input("Reject assignment (y/n)?")
        except ValueError:
            print("Sorry, I didn't understand that.")
            #better try again... Return to the start of the loop
            continue
        else:
            if response == 'y' or response == 'Y':
                print "Rejected"
                mtc.reject_assignment(assignmentId)
                break
            elif response == 'n' or response == 'N':
                print "Not rejected"
                break
            else:
                continue
    




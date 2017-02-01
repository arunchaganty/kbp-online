import boto
from boto.mturk.question  import ExternalQuestion
from connection import connect
import urllib
import argparse
import ConfigParser
import sys, os
import time
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('doc_paths_file', nargs=1, type=argparse.FileType('r'), default=sys.stdin, help="File or stdin containing documents paths")
parser.add_argument('config_file',  type=str, help="Config file containing parameters to spin the batch")
args = parser.parse_args()
config = ConfigParser.ConfigParser()
config.read(args.config_file)
mtc = connect(config.get('default', 'target'))
params = {'target': config.get('default', 'target')}
base_url = config.get('default', 'interface')+'?'
batch_info = []
for path in args.doc_paths_file[0]:
    params['doc_id'] = 'exhaustive/'+path.strip()
    url = base_url + urllib.urlencode(params)
    question = ExternalQuestion(url, config.get('default', 'frame_height'))
    response = mtc.create_hit(
            question=question,
            title=config.get('default', 'title'),
            description = config.get('default', 'description'),
            max_assignments = config.get('default', 'max_assignments'), 
            duration = config.get('default', 'duration'), 
            annotation = params['doc_id'], 
            lifetime = config.get('default', 'lifetime'), 
            reward = config.get('default', 'reward'))
    batch_info.append({'docId': params['doc_id'], 'HITTypeId': response[0].HITTypeId, 'HITId': response[0].HITId, })
metadata_dir = './batch/'
if not os.path.exists(metadata_dir):
    os.makedirs(metadata_dir) 
timestr = time.strftime("%Y%m%d-%H%M%S")
metadata_filepath = metadata_dir+args.config_file.split('/')[-1]+'.'+timestr+'.csv'
pd.DataFrame(batch_info).to_csv(path_or_buf = metadata_filepath, sep = '\t', index=False)

 




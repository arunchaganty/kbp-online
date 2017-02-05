import boto
from boto.mturk.question  import ExternalQuestion
from connection import connect
import urllib
import argparse
import ConfigParser
import sys, os
import time
import pandas as pd
import variablePricing
import codecs
import json

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
total_cost = 0
for doc_id in args.doc_paths_file[0]:
    doc_id = doc_id.strip()
    params['doc_id'] = config.get('default', 'doc_path_server')+doc_id.strip()
    doc = json.load(codecs.open(os.path.join(config.get('default', 'doc_path_script'), doc_id), 'r','utf-8'))
    if config.has_option('default', 'units_function') and config.has_option('default', 'unit_reward'):
        length = getattr(variablePricing, config.get('default', 'units_function'))(doc)
        reward = config.getfloat('default', 'unit_reward') * length
        est_time = int(config.getfloat('default', 'unit_time') * length)
        reward = float("{0:.2f}".format(reward))
        params['est_time'] = est_time
        params['reward'] = "{0:.2f}".format(reward)
        print length,  reward, params
    else:
        reward = config.getfloat('default', 'doc_reward')
        print reward, params
    url = base_url + urllib.urlencode(params)
    question = ExternalQuestion(url, config.get('default', 'frame_height'))
    total_cost += reward
    response = mtc.create_hit(
            question=question,
            title=config.get('default', 'title'),
            description = config.get('default', 'description'),
            max_assignments = config.get('default', 'max_assignments'), 
            duration = config.get('default', 'duration'), 
            annotation = params['doc_id'], 
            lifetime = config.get('default', 'lifetime'), 
            reward = reward)
    batch_info.append({'docId': params['doc_id'], 'HITTypeId': response[0].HITTypeId, 'HITId': response[0].HITId, })
metadata_dir = './batch/'
if not os.path.exists(metadata_dir):
    os.makedirs(metadata_dir) 
timestr = time.strftime("%Y%m%d-%H%M%S")
metadata_filepath = metadata_dir+args.config_file.split('/')[-1]+'.'+timestr+'.csv'
pd.DataFrame(batch_info).to_csv(path_or_buf = metadata_filepath, sep = '\t', index=False)
print "Total cost for all assignments", total_cost * config.getint('default', 'max_assignments')

 




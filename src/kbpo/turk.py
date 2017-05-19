import json
import logging

import boto
from boto.mturk.connection import MTurkConnection
from boto.mturk.question  import ExternalQuestion

from .api import get_document, get_evaluation_mention_pairs
from . import db

logger = logging.getLogger(__name__)

mturk_url = "kbpo.stanford.edu/tasks/do"

def unit_as_token(question):
    """Returns the number of tokens in a @question with parameter doc_id"""
    return sum(map(len, get_document(question['doc_id'])['sentences']))

def unit_as_mention_pair(doc_id):
    """Returns the number of mention_pairs in a @question with parameter doc_id"""
    return len(get_evaluation_mention_pairs(doc_id))

def connect(host_str, forced=False):
    """
    Connect to mechanical turk to sandbox or actual depending on
    @host_str with prompt for actual unless @forced
    """
    SANDBOX_HOST = 'mechanicalturk.sandbox.amazonaws.com'
    HOST = 'mechanicalturk.amazonaws.com'
    if  host_str == 'sandbox':
        host = SANDBOX_HOST
    elif host_str == 'actual':
        if not forced:
            proceed = input("This will connect to actual Mturk \
                    interface and cost money. Continue? (y/n)")
            if proceed in ['y', 'Y']:
                host = HOST
            else:
                logger.error("Aborting")
                exit(1)
        else:
            host = HOST

    mtc = MTurkConnection(host=host)
    logging.debug("Connected to "+host_str)
    return mtc

def compute_units(batch, question):
    """Compute length for a @question using the @batch parameters"""
    if 'units_function' in batch:
        length = locals()[batch['units_function']](question)
    else:
        length = 1
    return length

def compute_estimated_time(batch, question):
    """Compute estimated time for a @question using the @batch parameters"""
    length = compute_units(batch, question)
    if 'unit_time' in batch:
        est_time = int(batch['unit_time']) * length
    else:
        #TODO: Change default
        est_time = 60
    return est_time

def compute_reward(batch, question):
    """Compute reward for a @question using the @batch parameters"""
    length = compute_units(batch, question)
    if 'unit_reward' in batch:
        reward = float("{0:.2f}".format(batch['unit_reward'] * length))
    else:
        reward = batch['doc_reward']
    return reward

def create_hit(mturk_connection, batch, question):
    """
    Create a hit on mturk with @question in a @batch using @mturk_connection
    """
    reward = compute_reward(batch, question)
    #TODO: get the right url
    mturk_question = ExternalQuestion(mturk_url, batch['frame_height'])
    response = mturk_connection.create_hit(question=mturk_question,
                                           title=batch['title'],
                                           description=batch['description'],
                                           max_assignments=batch['max_assignments'],
                                           duration=batch['duration'],
                                           lifetime=batch['lifetime'],
                                           reward=reward)

    logging.debug("Created hit")
    logging.debug(response[0].HITTypeId, response[0].HITId)
    #batch_info.append({'docId': params['doc_id'], 'HITTypeId': , 'reward': reward, 'length': length})

def create_batch():
    raise NotImplementedError

def retrieve_assignments():
    raise NotImplementedError

def approve_assignments():
    raise NotImplementedError

if __name__ == '__main__':
    from .params.db.remote_kbpo_test import _PARAMS
    db.CONN = db.connect(_PARAMS)
    mturk_connection = connect('sandbox')
    batch = json.loads(next(db.select("SELECT params from mturk_batch WHERE batch_id = 20 LIMIT 1")))
    question = json.loads(next(db.select("SELECT params from mturk_batch WHERE question_batch_id = 12 LIMIT 1")))
    logging.debug("Batch and question retrieved")
    logging.debug(batch)
    logging.debug(question)
    create_hit(mturk_connection, batch, question)

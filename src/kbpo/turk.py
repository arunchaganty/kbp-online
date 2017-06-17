import logging
import json
import math
from psycopg2.extras import Json
from tqdm import tqdm

import boto3
#from boto.mturk.connection import MTurkConnection
from boto.mturk.question  import ExternalQuestion

import pytest
from .api import get_document, get_evaluation_mention_pairs
from . import db
from service.settings import MTURK_HOST

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
mturk_url = MTURK_HOST+"/tasks/do"
mturk_params_file = 'kbpo/params/mturk_params.json'

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
    sandbox_endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
    if  host_str == 'sandbox':
        mtc = boto3.client('mturk', endpoint_url=sandbox_endpoint_url)
    elif host_str == 'actual':
        proceed = False
        if not forced:
            proceed_input = input("This will connect to actual Mturk \
                    interface and cost money. Continue? (y/n)")
            if proceed_input in ['y', 'Y']:
                proceed = True
        else:
            proceed = True

        if proceed:
            mtc = boto3.client('mturk')
        else:
            logger.error("Aborting")
            exit(1)

    logger.debug("Connected to "+host_str+" mturk endpoint")
    logger.debug(mtc.get_account_balance())
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
    logger.debug(batch)
    reward = compute_reward(batch, question)
    mturk_question = ExternalQuestion(mturk_url, batch['frame_height'])
    response = mturk_connection.create_hit(Question=mturk_question.get_as_xml(),
                                           Title=batch['title'],
                                           Description=batch['description'],
                                           MaxAssignments=int(batch['max_assignments']),
                                           AssignmentDurationInSeconds=int(batch['duration']),
                                           LifetimeInSeconds=int(batch['lifetime']),
                                           Reward=reward)

    logger.debug(["HIT created: ", response['HIT']['HITTypeId'], response['HIT']['HITId']])
    #batch_info.append({'docId': params['doc_id'], 'HITTypeId': , 'reward':reward, 'length':length})
    return response['HIT']['HITTypeId'], response['HIT']['HITId']

def test_create_hit():
    """Test hit creation on the sandbox"""
    from .params.db.remote_kbpo_test import _PARAMS
    db.CONN = db.connect(_PARAMS)
    mturk_connection = connect('sandbox')
    batch = next(db.select("SELECT params from mturk_batch WHERE id = 20 LIMIT 1"))[0]
    question = next(db.select(
        "SELECT params from evaluation_question WHERE batch_id = 12 LIMIT 1"))[0]
    logger.debug("Batch and question retrieved")
    logger.debug(batch)
    logger.debug(question)
    create_hit(mturk_connection, batch, question)


def percentage_to_whole_range(size, range_begin=None, range_end=None):
    """Transforms fractional ranges to integer ranges scaled by size"""
    assert range_begin != None or range_end != None, \
            "At least one endpoint of the range needs to be specified"
    if range_begin is None:
        range_begin = 0
    if range_end is None:
        range_end = 1
    assert abs(range_begin) <= 1 and abs(range_end) <= 1, \
            "Both endpoints should have fractional limits"
    assert size >= 1, "size should be non-zero"

    i_begin = math.floor(range_begin*size)
    i_end = math.floor(range_end*size)
    i_begin, i_end = integer_to_whole_range(size, range_begin=i_begin, range_end=i_end)

    return i_begin, i_end

def integer_to_whole_range(size, range_begin=None, range_end=None):
    """Transforms integer ranges to whole number ranges"""
    assert range_begin != None or range_end != None, \
            "At least one endpoint of the range needs to be specified"
    assert size >= 1, "size should be non-zero"
    i_begin, i_end = range_begin, range_end
    if range_begin < 0:
        i_begin = size + i_begin
    if i_end < 0:
        i_end = size + i_end
    return i_begin, i_end

def test_transform_percentage_to_integer_range():
    """Test the above transformation"""
    with pytest.raises(AssertionError, message="Non-zero size expected"):
        percentage_to_whole_range(0)

    with pytest.raises(AssertionError, message="Expecting at least one range endpoint"):
        percentage_to_whole_range(10)

    with pytest.raises(AssertionError, message="Expecting at least one range endpoint"):
        percentage_to_whole_range(10, range_begin=None, range_end=None)

    with pytest.raises(AssertionError, message="Expecting range endpoints to be a positive or negative fraction"):
        percentage_to_whole_range(10, range_begin=0, range_end=2)

    with pytest.raises(AssertionError, message="Expecting range endpoints to be a positive or negative fraction"):
        percentage_to_whole_range(10, range_begin=None, range_end=-2)

    assert percentage_to_whole_range(10, range_begin=0.1, range_end=0.8) == (1, 8)
    assert percentage_to_whole_range(10, range_begin=-0.9, range_end=-0.2) == (1, 8)
    assert percentage_to_whole_range(13, range_begin=-0.9, range_end=-0.2) == (1, 10)


def create_batch(db, mturk_connection, batch_id, range_type=None, range_begin=None, range_end=None):
    """
    Create a batch of hits on mturk with @range_begin and @range_end as the 
    @range_type (percentage/integer) range
    of questions in a @batch using @mturk_connection with @mturk_params.
    Uses @db with its own connection from kbpo.db
    The resulting HITs are stored in mturk_hit table corresponding to an 
    mturk_batch
    """
    batch_size = next(db.select(
        "SELECT count(*) from evaluation_question WHERE batch_id = %(batch_id)s", batch_id=batch_id))[0]
    logger.debug(batch_size)
    batch_type = next(db.select(
        "SELECT batch_type from evaluation_batch WHERE id = %(batch_id)s", batch_id=batch_id)).batch_type
    if range_type is None:
        assert range_begin is None and range_end is None, "Specify range type"
        range_type = 'percentage'
        range_begin = 0
        range_end = 1

    if range_type is 'percentage':
        begin, end = percentage_to_whole_range(batch_size, range_begin, range_end)
    elif range_type is 'integer':
        begin, end = integer_to_whole_range(batch_size, range_begin, range_end)
    with open(mturk_params_file, 'r') as f:
        mturk_params = json.load(f)[batch_type]

    questions = db.select(
        """SELECT id, params from evaluation_question WHERE
        batch_id = %(batch_id)s ORDER BY id OFFSET %(range_begin)s LIMIT %(limit)s""",
        batch_id=batch_id,
        range_begin=begin,
        limit=end-begin
        )

    #TODO: Have a meaningful autogenerated description
    with db.CONN:
        with db.CONN.cursor() as cur:
            db.execute("""INSERT INTO mturk_batch (params, description)
                                      VALUES (%(mturk_params)s, %(description)s) RETURNING id""", cur = cur,
                                      mturk_params=Json(mturk_params), description="")
            mturk_batch_id = cur.fetchone()[0]
            logger.debug(['mturk_batch_id', mturk_batch_id])
            for question in tqdm(questions):
                hit_type_id, hit_id = create_hit(mturk_connection, mturk_params, question.params)
                db.execute(
                    """INSERT INTO mturk_hit (id, batch_id, question_batch_id, question_id, type_id, price, units)
                       VALUES (%(hit_id)s, %(batch_id)s, %(question_batch_id)s,
                       %(question_id)s, %(hit_type_id)s, %(price)s, %(units)s)""", cur = cur,
                    hit_id=hit_id,
                    batch_id=mturk_batch_id,
                    question_batch_id=batch_id,
                    question_id=question.id,
                    hit_type_id=hit_type_id,
                    price=compute_reward(mturk_params, question),
                    units=compute_units(mturk_params, question))
                logger.debug({'hit_id': hit_id, 'mturk_batch_id': mturk_batch_id,
                              'question_id': question.id, 'question_batch_id': batch_id})

def test_create_batch():
    """Test batch creation on the sandbox"""
    from .params.db.remote_kbpo_test import _PARAMS
    db.CONN = db.connect(_PARAMS)
    mturk_connection = connect('sandbox')
    batch_id = 12
    logger.debug("Creating a mturk batch using first 10% question from evaluation_batch_id=9")
    #create_batch(db,mturk_connection, batch_id, range_type='integer', range_begin = 0, range_end = 5)
    create_batch(db,mturk_connection, batch_id)
    #create_batch(db,mturk_connection, batch, range_type='percentage', range_begin = '0.1', range_end = '0.2')

    
def retrieve_assignments():
    raise NotImplementedError

def approve_assignments():
    raise NotImplementedError

if __name__ == '__main__':
    test_create_batch()

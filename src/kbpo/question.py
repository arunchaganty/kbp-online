import logging
import json
import hashlib
from psycopg2.extras import Json
from tqdm import tqdm

from . import db


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def create_selective_relation_question(batch_id, doc_id, mention_1, mention_2, cur = None):
    raise NotImplementedError

def create_evaluation_batch_from_submission_sample(batch_id):
    #Contains all questions asked
    corpus_tag, name, details, distribution = next(db.select(
        """
        SELECT DISTINCT s.corpus_tag, name, details, distribution_type
        FROM submission AS s 
        JOIN submission_sample AS ss 
            ON ss.submission_id = s.id 
        JOIN sample_batch AS sb 
            ON sb.id = ss.batch_id
        WHERE ss.batch_id = %(batch_id)s;
        """, batch_id = batch_id))
    existing_questions = list(db.select(
    """SELECT params->>'doc_id' AS doc_id, 
              params->'mention_1' AS m1, 
              params->'mention_2' AS m2 
        FROM evaluation_question 
        WHERE params->>'batch_type' = 'selective_relations';"""
    ))

    
    #Just for surety (as the response data could have been loaded from a separate source, i.e. without having been created as an evaluation question)
    existing_responses = list(db.select(
    """
    SELECT doc_id, subject AS m1, object AS m2 from evaluation_relation;
    """
    ))
    existing = set([(m.doc_id, tuple(m.m1[1:]), tuple(m.m2[1:])) for m in existing_questions] + 
            [(m.doc_id, (m.m1.lower, m.m1.upper), (m.m2.lower, m.m2.upper)) for m in existing_responses] +
            [(m.doc_id, tuple(m.m2[1:]), tuple(m.m1[1:])) for m in existing_questions] + 
            [(m.doc_id, (m.m2.lower, m.m2.upper), (m.m1.lower, m.m1.upper)) for m in existing_responses])
    
    

    new_questions = db.select(
            """
            SELECT doc_id, subject AS m1, object AS m2 from submission_sample WHERE batch_id = %(batch_id)s;
            """, batch_id = batch_id)
    proposed = set([(m.doc_id, (m.m1.lower, m.m1.upper), (m.m2.lower, m.m2.upper)) for m in new_questions])
    new_questions = proposed - existing 

    if len(list(new_questions)) > 0:
        with db.CONN:
            with db.CONN.cursor() as cur:
                description = "%d unique instances sampled from submission %s (%s) using distribution %s" % (len(list(new_questions)), name, details, distribution)
                evaluation_batch_id = next(db.select("""INSERT INTO evaluation_batch 
                            (batch_type, corpus_tag, description) 
                            VALUES (%(batch_type)s, %(corpus_tag)s, %(description)s) RETURNING id""", cur = cur, 
                            batch_type = 'selective_relations', corpus_tag = corpus_tag, description = description))
                values = []
                for q in tqdm(list(new_questions)):
                    m = hashlib.md5()
                    doc_id, m1, m2 = q
                    params = {'batch_type': 'selective_relations', 'mention_1': [doc_id, m1[0], m1[1]], 'mention_2': [doc_id, m2[0], m2[1]], 'doc_id': doc_id}
                    params_json = json.dumps(params, sort_keys = True)
                    m.update(params_json.encode('utf-8'))
                    row_id = m.hexdigest()
                    values.append((evaluation_batch_id.id, row_id, params_json, 'not_turked'))

                db.execute_values(cur, "INSERT INTO evaluation_question(batch_id, id, params, state) VALUES %s", 
                        values)
    else:
        logger.warning("All the samples have already been asked as questions")
    return evaluation_batch_id

    


if __name__ == '__main__':
    create_evaluation_batch_from_submission_sample(11)

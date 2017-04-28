#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database utilities.
"""

import logging
import re
import psycopg2 as db
from psycopg2.extras import execute_values, register_composite
from .kbpo_db_params import _PARAMS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def connect(params=_PARAMS):
    """Connect to database using @params"""
    conn = db.connect(**params)
    with conn:
        with conn.cursor() as _cur:
            _cur.execute("SET search_path TO kbpo;")
            # TODO: put this in the db/custom cursor class @arun, done?
    return conn

CONN = None

try:
    CONN = connect()
except:
    logging.error("Unable to connect to database")

def select(sql, **kwargs):
    """Wrapper around psycopg execute function to yield the result of a SELECT statement"""
    with CONN:
        with CONN.cursor() as cur:
            register_composite('kbpo.span', cur)
            cur.execute(sql, kwargs)
            yield from cur

def execute(sql, **kwargs):
    """Wrapper around psycopg execute function to not yield the result of execute statement"""
    with CONN:
        with CONN.cursor() as cur:
            register_composite('kbpo.span', cur)
            cur.execute(sql, kwargs)

def sanitize(word):
    """
    Remove any things that would confusing psql.
    """
    return re.sub(r"[^a-zA-Z0-9. ]", "%", word)

def random_sample(field, table, sample_size=1):
    """
    Get a randomly sampled field from a table
    """
    qry = """
    SELECT COUNT(*) FROM {table};
    """.format(table=table)
    num = next(select(qry))
    qry = """
    SELECT {field} FROM {table} OFFSET floor(random()*%(N)s) LIMIT %(sample_size)s;
    """.format(table=table, field=field)
    return select(qry, field=field, table=table, N=num, sample_size=sample_size)

def query_docs(corpus_id, sentence_table="sentence"):
    """
    List all doc_ids from @corpus_id
    """
    qry = """
SELECT DISTINCT(doc_id) 
FROM {sentence}
WHERE corpus_id = {corpus_id}
  AND doc_id IN (SELECT doc_id FROM document_date)
ORDER BY doc_id"""

    return select(qry.format(corpus_id=corpus_id, sentence=sentence_table))

def query_wikilinks(fb_ids):
    """Map to wikilink based on @fb_ids"""
    qry = "SELECT fb_id, wiki_id FROM fb_to_wiki_map WHERE fb_id IN %(fb_ids)s"
    return select(qry, fb_ids=fb_ids)

def query_entity_docs(entities):
    """
    TODO: @Arun add description
    """
    cur = CONN.cursor()
    cur.execute("DROP TABLE IF EXISTS _query_entities;")
    cur.execute("CREATE TEMPORARY TABLE _query_entities(gloss TEXT);")
    execute_values(cur, "INSERT INTO _query_entities(gloss) VALUES %s", 
                   [(entity,) for entity, _ in entities])
    cur.execute("""
SELECT q.gloss, array_agg(DISTINCT doc_id)
FROM mention m, _query_entities q
WHERE m.gloss = q.gloss
GROUP BY q.gloss
""")
    docs = {k: vs for k, vs in cur.fetchall()}

    CONN.commit()
    cur.close()

    return docs

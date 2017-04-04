#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database utilities.
"""

import re
import time
import psycopg2 as db
from psycopg2.extras import execute_values, NamedTupleCursor, register_composite

from .defs import NER_MAP

# File wide connection.
_PARAMS = {
    'dbname':'kbp',
    'user':'kbp',
    'host':'localhost',
    'port':4242,
    'cursor_factory': NamedTupleCursor,
    }
CONN = db.connect(**_PARAMS)
with CONN:
    with CONN.cursor() as _cur:
        _cur.execute("SET search_path TO kbpo;")

def select(sql, **kwargs):
    with CONN:
        with CONN.cursor() as cur:
            cur.execute(sql, kwargs)
            yield from cur

def sanitize(word):
    """
    Remove any things that would confusing psql.
    """
    return re.sub(r"[^a-zA-Z0-9. ]", "%", word)

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
    qry = "SELECT fb_id, wiki_id FROM fb_to_wiki_map WHERE fb_id IN %(fb_ids)s"
    return select(qry, fb_ids=fb_ids)

def query_entities(doc_ids, mention_table="mention"):
    """
    Get all (canonical) entities across these @doc_ids.
    """
    qry = """
SELECT max(gloss), COUNT(DISTINCT doc_id)
FROM {mention} m
WHERE doc_canonical_char_begin = doc_char_begin AND doc_canonical_char_end = doc_char_end 
AND is_entity_type(ner)
AND doc_id IN %(doc_ids)s
GROUP BY best_entity"""
    return select(qry.format(mention=mention_table), doc_ids=tuple(doc_ids))

def query_dates(doc_ids):
    """
    Get all dates for these @doc_ids.
    """
    # TODO: I shouldn't be formatting figures.
    qry = """
SELECT doc_id, date
FROM document_date 
WHERE doc_id IN ({doc_ids})"""
    return select(qry.format(doc_ids=",".join("'{}'".format(d) for d in doc_ids)))

def query_doc(docid, sentence_table="sentence"):
    doc = []
    T = {
        "-LRB-": "(",
        "-RRB-": ")",
        "-LSB-": "[",
        "-RSB-": "]",
        "-LCB-": "{",
        "-RCB-": "}",
        "``": "\"",
        "''": "\"",
        "`": "'",
        }
    qry = """
SELECT sentence_index, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end 
FROM {sentence}
WHERE doc_id = '{}'
ORDER BY sentence_index
"""

    for row in select(qry.format(docid, sentence=sentence_table)):
        _, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = row

        # Happens in some DF
        #assert int(idx) == idx_, "Seems to have skipped a line: {} != {}".format(idx, idx_)
        words = list(map(lambda w: T.get(w, w), words))
        doc_char_begin, doc_char_end = map(int, doc_char_begin), map(int, doc_char_end)
        keys = ("word", "lemma", "pos_tag", "ner_tag", "doc_char_begin", "doc_char_end")
        tokens = [{k:v for k, v in zip(keys, values)} for values in zip(words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end)]
        doc.append(tokens)
    return doc

def query_mentions(docid, mention_table="mention"):
    qry = """SELECT m.gloss, n.ner, m.doc_char_begin, m.doc_char_end, n.gloss AS canonical_gloss, m.best_entity, m.doc_canonical_char_begin, m.doc_canonical_char_end
    FROM {mention} m, {mention} n 
    WHERE m.doc_id = %(doc_id)s AND n.doc_id = m.doc_id 
      AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end 
      AND n.parent_id IS NULL
    ORDER BY m.doc_char_begin"""
    mentions = []
    for row in select(qry.format(mention=mention_table), doc_id=docid):
        gloss, ner, doc_char_begin, doc_char_end, entity_gloss, entity_link, entity_doc_char_begin, entity_doc_char_end = row
        if ner not in NER_MAP: continue
        ner = NER_MAP[ner]

        mentions.append({
            "gloss": gloss,
            "type": ner,
            "doc_char_begin": int(doc_char_begin),
            "doc_char_end": int(doc_char_end),
            "entity": {
                "gloss": entity_gloss,
                "link": entity_link,
                "doc_char_begin": int(entity_doc_char_begin),
                "doc_char_end": int(entity_doc_char_end),
                }
            })
    return mentions

def query_mentions_by_id(mention_ids, mention_table="mention"):
    with CONN.cursor() as cur:
        cur.execute("""
        CREATE TEMPORARY TABLE _mentions (doc_id TEXT, id INTEGER);
        """)
        execute_values(cur, """INSERT INTO _mentions VALUES %s""", mention_ids)
        cur.execute("""
SELECT DISTINCT ON(m.doc_id, m.doc_char_begin, m.doc_char_end) m.id, n.ner, m.gloss, m.doc_id, m.doc_char_begin, m.doc_char_end, m.best_entity, n.id AS canonical_id, n.canonical_doc_char_begin, n.canonical_doc_char_end
FROM {mention} m, {mention} n, _mentions o
WHERE m.id = o.id AND m.doc_id = o.doc_id
  AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
  AND m.parent_id IS NULL
  AND n.parent_id IS NULL
ORDER BY m.doc_id, m.doc_char_begin, m.doc_char_end
""".format(mention=mention_table))
        ret = list(cur)
        cur.execute("""DROP TABLE _mentions""")
    return ret

def query_mention_ids(mention_ids, mention_table="mention"):
    with CONN.cursor() as cur:
        cur.execute("""
        CREATE TEMPORARY TABLE _mentions (id INTEGER);
        """)
        execute_values(cur, """INSERT INTO _mentions VALUES %s""", mention_ids)
        cur.execute("""
    SELECT m.doc_id, m.id
      FROM {mention} m, {mention} n, _mentions o
     WHERE m.id = o.id
       AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
       AND m.parent_id IS NULL
       AND n.parent_id IS NULL
    UNION
    SELECT n.doc_id, n.id
      FROM {mention} m, {mention} n, _mentions o
     WHERE m.id = o.id
       AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
       AND m.parent_id IS NULL
       AND n.parent_id IS NULL
    """.format(mention=mention_table))
        ret = set(cur)
        cur.execute("""DROP TABLE _mentions""")
    return ret

def query_entity_docs(entities):
    cur = CONN.cursor()
    cur.execute("DROP TABLE IF EXISTS _query_entities;")
    cur.execute("CREATE TEMPORARY TABLE _query_entities(gloss TEXT);")
    execute_values(cur, "INSERT INTO _query_entities(gloss) VALUES %s", [(entity,) for entity, _ in entities])
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

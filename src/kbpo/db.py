#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database utilities.
"""

import re
import psycopg2 as db
from psycopg2.extras import execute_values, NamedTupleCursor

from .defs import ner_map

# File wide connection.
_PARAMS = {
    'dbname':'kbp',
    'user':'kbp',
    'host':'localhost',
    'port':4242,
    'cursor_factory': NamedTupleCursor,
    }
_CONN = db.connect(**_PARAMS)
with _CONN.cursor() as _cur:
    _cur.execute("SET search_path TO kbpo;")

def pg_select(sql, **kwargs):
    with _CONN.cursor() as cur:
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

    return pg_select(qry.format(corpus_id=corpus_id, sentence=sentence_table))

def query_wikilinks(fb_ids):
    qry = "SELECT fb_id, wiki_id FROM fb_to_wiki_map WHERE fb_id IN %(fb_ids)s"
    return pg_select(qry, fb_ids=fb_ids)

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
    return pg_select(qry.format(mention=mention_table), doc_ids=tuple(doc_ids))

def query_dates(doc_ids):
    """
    Get all dates for these @doc_ids.
    """
    qry = """
SELECT doc_id, date
FROM document_date 
WHERE doc_id IN ({doc_ids})"""
    return pg_select(qry.format(doc_ids=",".join("'{}'".format(d) for d in doc_ids)))

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

    for row in pg_select(qry.format(docid, sentence=sentence_table)):
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
    WHERE m.doc_id = '{doc_id}' AND n.doc_id = m.doc_id 
      AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end 
      AND n.parent_id IS NULL
    ORDER BY m.doc_char_begin"""
    mentions = []
    for row in pg_select(qry.format(doc_id=docid, mention=mention_table)):
        gloss, ner, doc_char_begin, doc_char_end, entity_gloss, entity_link, entity_doc_char_begin, entity_doc_char_end = row
        if ner not in ner_map: continue
        ner = ner_map[ner]

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
    qry = """
SELECT DISTINCT ON(doc_id, doc_char_begin, doc_char_end) m.id, n.ner, m.gloss, m.doc_id, m.doc_char_begin, m.doc_char_end, m.best_entity, n.id
FROM {mention} m, {mention} n
WHERE m.id IN %s
  AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
  AND m.parent_id IS NULL
  AND n.parent_id IS NULL
ORDER BY doc_id, doc_char_begin, doc_char_end
"""
    return pg_select(qry.format(mention=mention_table), mention_ids)

def query_mention_ids(mention_ids, mention_table="mention"):
    qry = """
SELECT m.id
  FROM {mention} m, {mention} n
 WHERE m.id IN %s
   AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
   AND m.parent_id IS NULL
   AND n.parent_id IS NULL
UNION
SELECT n.id
  FROM {mention} m, {mention} n
 WHERE m.id IN %s
   AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
   AND m.parent_id IS NULL
   AND n.parent_id IS NULL
"""
    return set(m for m, in pg_select(qry.format(mention=mention_table), mention_ids))

def query_entity_docs(entities):
    cur = _CONN.cursor()
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

    _CONN.commit()
    cur.close()

    return docs

"""
Utilities connecting the web interface to database
Interfacing with database API
"""
from datetime import date, datetime

from . import db
from . import defs

def get_documents(corpus_tag):
    """
    Returns a list of documents with a particualr corpus tag
    """
    return db.select("""
        SELECT doc_id
        FROM document_tag
        WHERE tag=%(tag)s
        ORDER BY doc_id
        """, tag=corpus_tag)

def test_get_documents():
    docs = list(get_documents("kbp-2016"))
    assert len(docs) == 15000
    assert "NYT_ENG_20131216.0031" in docs

def get_document(doc_id):
    """
    Returns id, date, title and sentences for a given @doc_id
    """
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

    doc_info = next(db.select("""
        SELECT id, title, doc_date
        FROM document
        WHERE id = %(doc_id)s
        """, doc_id=doc_id))
    assert doc_info.id == doc_id

    sentences = []
    for row in db.select("""
            SELECT sentence_index, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end 
            FROM sentence
            WHERE doc_id = %(doc_id)s
            ORDER BY sentence_index
            """, doc_id=doc_id):
        _, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = row

        words = list(map(lambda w: T.get(w, w), words))
        doc_char_begin, doc_char_end = map(int, doc_char_begin), map(int, doc_char_end)
        keys = ("word", "lemma", "pos_tag", "ner_tag", "doc_char_begin", "doc_char_end")
        sentence = [{k:v for k, v in zip(keys, values)} for values in zip(words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end)]
        sentences.append(sentence)
    doc = {
        "id": doc_id,
        "date": doc_info.doc_date,
        "title": doc_info.title,
        "sentences": sentences,
    }
    return doc

def test_get_document():
    doc_id = "NYT_ENG_20131216.0031"
    doc = get_document(doc_id)
    assert doc["id"] == doc_id
    assert doc["title"] == "A GRAND WEEKEND OUT FOR PENNSYLVANIANS AS LEADERS GATHER IN NEW YORK"
    assert doc["date"] == date(2013, 12, 16)
    assert len(doc["sentences"]) == 25

    sentence = doc["sentences"][0]

    assert len(sentence) == 12
    assert "A GRAND WEEKEND OUT FOR PENNSYLVANIANS AS LEADERS GATHER IN NEW YORK".split() == [t["word"] for t in sentence]
    assert "a GRAND WEEKEND OUT for PENNSYLVANIANS as leader gather in new YORK".split() == [t["lemma"] for t in sentence]
    assert "DT NNP NNP NNP IN NNPS JJ NNS VBP IN JJ NNP".split() == [t["pos_tag"] for t in sentence]

    assert doc["id"] == "NYT_ENG_20131216.0031"

def get_suggested_mentions(doc_id):
    """
    Get suggested mentions for a document.
    """
    mentions = []
    for row in db.select("""
            SELECT m.id, m.gloss, m.mention_type, n.id AS canonical_id, n.gloss AS canonical_gloss, l.link_name
            FROM suggested_mention m, suggested_mention n, suggested_link l
            WHERE m.doc_id = n.doc_id AND m.canonical_id = n.id
              AND n.doc_id = l.doc_id AND n.id = l.id
              AND m.doc_id = %(doc_id)s
            ORDER BY m.id
            """, doc_id=doc_id):
        mention = {
            "span": row.id,
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": row.canonical_id,
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_suggested_mentions():
    doc_id = "NYT_ENG_20131216.0031"
    mentions = get_suggested_mentions(doc_id)
    assert len(mentions) == 91
    mention = mentions[13]
    assert mention == {
        'span': ("NYT_ENG_20131216.0031", 506, 521),
        'gloss': 'Waldorf-Astoria',
        'type': 'LOCATION',
        'entity': {
            'span': ("NYT_ENG_20131216.0031", 506, 521),
            'gloss': 'Waldorf-Astoria',
            'link': 'The_Waldorf-Astoria_Hotel',
            },
        }

def get_suggested_mention_pairs(doc_id):
    """
    Get mention pairs for suggsted mentions for a document.
    """
    mention_pairs = set()
    for row in db.select("""
            SELECT m.id AS subject_id, m.mention_type AS subject_type, n.id AS object_id, n.mention_type AS object_type
            FROM suggested_mention m, suggested_mention n
            WHERE m.doc_id = n.doc_id AND m.sentence_id = n.sentence_id
              AND m.doc_id = %(doc_id)s
              AND m.id <> n.id
              AND is_entity_type(m.mention_type)
            ORDER BY subject_id, object_id
            """, doc_id=doc_id):
        # Pick up any subject pairs that are of compatible types.
        if (row.subject_type, row.object_type) not in defs.VALID_MENTION_TYPES: continue
        # Check that this pair doesn't already exist.
        if (row.object_id, row.subject_id) in mention_pairs: continue
        mention_pairs.add((row.subject_id, row.object_id))
    return [{"subject_id": subject_id, "object_id": object_id} for subject_id, object_id in sorted(mention_pairs)]

def test_get_suggested_mention_pairs():
    doc_id = "NYT_ENG_20131216.0031"
    pairs = get_suggested_mention_pairs(doc_id)
    assert len(pairs) == 70
    pair = pairs[0]
    assert tuple(pair['subject_id']) == ('NYT_ENG_20131216.0031', 371, 385)
    assert tuple(pair['object_id']) == ('NYT_ENG_20131216.0031', 360, 368)

def get_submission_mentions(doc_id, submission_id):
    """
    Get suggested mentions for a document.
    """
    mentions = []
    for row in db.select("""
            SELECT m.mention_id, m.gloss, m.mention_type, m.canonical_id, n.gloss AS canonical_gloss, l.link_name
            FROM submission_mention m, submission_mention n, submission_link l
            WHERE m.doc_id = n.doc_id AND m.canonical_id = n.mention_id AND m.submission_id = n.submission_id
              AND n.doc_id = l.doc_id AND n.mention_id = l.mention_id AND n.submission_id = l.submission_id
              AND m.doc_id = %(doc_id)s
              AND m.submission_id = %(submission_id)s
            ORDER BY m.mention_id
            """, doc_id=doc_id, submission_id=submission_id):
        mention = {
            "span": row.mention_id,
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": row.canonical_id,
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_submission_mentions():
    doc_id = "NYT_ENG_20131216.0031"
    mentions = get_submission_mentions(doc_id, 15)
    assert len(mentions) == 10
    mention = mentions[0]
    assert mention == {
        'span' : ("NYT_ENG_20131216.0031", 1261, 1278),
        'gloss': 'Edward G. Rendell',
        'type': 'PER',
        'entity': {
            'span' : ("NYT_ENG_20131216.0031", 1261, 1278),
            'gloss': 'Edward G. Rendell',
            'link': 'Ed_Rendell',
            },
        }

def get_evaluation_mention_pairs(doc_id):
    """
    Get mention pairs from exhaustive mentions for a document.
    """
    mention_pairs = set()
    for row in db.select("""
            SELECT m.mention_id AS subject_id, m.mention_type AS subject_type, n.mention_id AS object_id, n.mention_type AS object_type
            FROM evaluation_mention m, evaluation_mention n, evaluation_batch b, sentence s
            WHERE m.question_batch_id = n.question_batch_id AND m.question_id = n.question_id 
              AND m.doc_id = n.doc_id
              AND m.question_batch_id = b.id
              AND m.doc_id = s.doc_id AND m.mention_id <@ s.span AND n.mention_id <@ s.span
              AND m.doc_id = %(doc_id)s
              AND m.mention_id <> n.mention_id
              AND b.batch_type = 'exhaustive_entities'
              AND is_entity_type(m.mention_type)
            ORDER BY subject_id, object_id
            """, doc_id=doc_id):
        # Pick up any subject pairs that are of compatible types.
        if (row.subject_type, row.object_type) not in defs.VALID_MENTION_TYPES: continue
        # Check that this pair doesn't already exist.
        if (row.object_id, row.subject_id) in mention_pairs: continue
        mention_pairs.add((row.subject_id, row.object_id))
    return [{"subject_id": subject_id, "object_id": object_id} for subject_id, object_id in sorted(mention_pairs)]

def test_get_evaluation_mention_pairs():
    doc_id = "NYT_ENG_20131216.0031"
    pairs = get_suggested_mention_pairs(doc_id)
    assert len(pairs) == 70
    pair = pairs[0]
    assert tuple(pair['subject_id']) == ('NYT_ENG_20131216.0031', 371, 385)
    assert tuple(pair['object_id']) == ('NYT_ENG_20131216.0031', 360, 368)

def get_submission_relations(doc_id, submission_id):
    """
    Get suggested mentions for a document.
    """
    relations = []
    for row in db.select("""
            SELECT subject_id, relation, object_id, provenances, confidence
            FROM submission_relation
            WHERE doc_id = %(doc_id)s
              AND submission_id = %(submission_id)s
            ORDER BY subject_id
            """, doc_id=doc_id, submission_id=submission_id):
        assert len(row.provenances) > 0, "Invalid submission entry does not have any provenances"
        provenance = row.provenances
        relation = {
            "subject": row.subject_id,
            "relation": row.relation,
            "object": row.object_id,
            "doc_char_begin": provenance[0],
            "doc_char_end": provenance[1],
            "confidence": row.confidence,
            }
        relations.append(relation)
    return relations

def test_get_submission_relations():
    doc_id = "NYT_ENG_20131216.0031"
    relations = get_submission_relations(doc_id, 15)
    assert len(relations) == 5
    relation = relations[0]

    assert relation == {
        "subject": ('NYT_ENG_20131216.0031',1261,1278),
        "relation": 'per:title',
        "object": ('NYT_ENG_20131216.0031',1300,1308),
        "doc_char_begin": 1261,
        "doc_char_end": 1278,
        "confidence": 0.
        }

def insert_assignment(
        assignment_id, hit_id, worker_id,
        worker_time, comments, response,
        status="Submitted", created=datetime.now()):
    batch_id = next(db.select("""SELECT batch_id FROM mturk_hit WHERE id = %(hit_id)s;""", hit_id=hit_id))

    db.execute("""
        INSERT INTO mturk_assignment (id, hit_id, batch_id, worker_id, created, worker_time, response, comments, status) 
        VALUES (%(assignment_id)s, %(hit_id)s, %(batch_id)s, %(worker_id)s, %(created)s, %(worker_time)s, %(response)s, %(comments)s, %(status)s)""",
               assignment_id=assignment_id,
               hit_id=hit_id,
               batch_id=batch_id,
               worker_id= worker_id,
               created= created,
               worker_time=int(float(worker_time)),
               response=response,
               comments=comments,
               status=status)

def get_hits(limit=None):
    if limit is None:
        return db.select("""SELECT * FROM mturk_hit""")
    else:
        return db.select("""SELECT * FROM mturk_hit LIMIT %(limit)s""", limit=limit)

def get_hit(hit_id):
    return next(db.select("""SELECT * FROM mturk_hit WHERE hit_id=%(hit_id)s""", hit_id=hit_id))

def get_task_params(hit_id):
    return next(db.select("""
        SELECT params 
        FROM mturk_hit h 
        JOIN evaluation_question q ON (h.question_batch_id = q.batch_id AND h.question_id = q.id)
        WHERE h.id=%(hit_id)s""", hit_id=hit_id)).params

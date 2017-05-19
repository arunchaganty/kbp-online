"""
Utilities connecting the web interface to database
Interfacing with database API
"""
import json
from datetime import date, datetime
from hashlib import sha1

from . import db
from . import defs

def get_documents(corpus_tag):
    """
    Returns a list of documents with a particular corpus tag
    """
    values = db.select("""
        SELECT doc_id
        FROM document_tag
        WHERE tag=%(tag)s
        ORDER BY doc_id
        """, tag=corpus_tag)
    return (x.doc_id for x in values)

def test_get_documents():
    docs = list(get_documents("kbp2016"))
    assert len(docs) == 15001
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
            SELECT sentence_index, token_spans, words, lemmas, pos_tags, ner_tags
            FROM sentence
            WHERE doc_id = %(doc_id)s
            ORDER BY sentence_index
            """, doc_id=doc_id):
        _, token_spans, words, lemmas, pos_tags, ner_tags = row

        words = list(map(lambda w: T.get(w, w), words))
        token_spans = [(span.lower, span.upper) for span in token_spans]
        keys = ("word", "lemma", "pos_tag", "ner_tag", "span",)
        sentence = [{k:v for k, v in zip(keys, values)} for values in zip(words, lemmas, pos_tags, ner_tags, token_spans)]
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
            SELECT m.span, m.gloss, m.mention_type, n.span AS canonical_span, n.gloss AS canonical_gloss, l.link_name
            FROM suggested_mention m
            JOIN suggested_mention n ON (m.doc_id = n.doc_id AND m.canonical_span = n.span)
            LEFT OUTER JOIN suggested_link l ON (n.doc_id = l.doc_id AND n.span = l.span)
            WHERE m.doc_id = %(doc_id)s
            ORDER BY m.span
            """, doc_id=doc_id):
        mention = {
            "span": (row.span.lower, row.span.upper),
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": (row.canonical_span.lower, row.canonical_span.upper),
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_suggested_mentions():
    doc_id = "NYT_ENG_20131216.0031"
    mentions = get_suggested_mentions(doc_id)
    assert len(mentions) == 73
    mention = mentions[11]
    assert mention == {
        'span': (506, 521),
        'gloss': 'Waldorf-Astoria',
        'type': 'GPE',
        'entity': {
            'span': (506, 521),
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
            SELECT m.span AS subject, m.mention_type AS subject_type, n.span AS object, n.mention_type AS object_type
            FROM suggested_mention m, suggested_mention n
            WHERE m.doc_id = n.doc_id AND m.sentence_id = n.sentence_id
              AND m.doc_id = %(doc_id)s
              AND m.span <> n.span
              AND m.canonical_span <> n.canonical_span
              AND is_entity_type(m.mention_type)
            ORDER BY subject, object
            """, doc_id=doc_id):
        # Pick up any subject pairs that are of compatible types.
        if (row.subject_type, row.object_type) not in defs.VALID_MENTION_TYPES: continue
        # Remove pairs which have the same canonical span
        # Check that this pair doesn't already exist.
        if (row.object, row.subject) in mention_pairs: continue
        mention_pairs.add((row.subject, row.object))
    return [{"subject": (subject.lower, subject.upper), "object": (object_.lower, object_.upper)} for subject, object_ in sorted(mention_pairs)]

def test_get_suggested_mention_pairs():
    doc_id = "NYT_ENG_20131216.0031"
    pairs = get_suggested_mention_pairs(doc_id)
    assert len(pairs) == 70
    pair = pairs[0]
    assert pair['subject'] == (371, 385)
    assert pair['object'] == (360, 368)

def get_submission_mentions(submission_id, doc_id):
    """
    Get suggested mentions for a document.
    """
    mentions = []
    for row in db.select("""
            SELECT m.span, m.gloss, m.mention_type, m.canonical_span, n.gloss AS canonical_gloss, l.link_name
            FROM submission_mention m
            JOIN submission_mention n ON (m.doc_id = n.doc_id AND m.canonical_span = n.span AND m.submission_id = n.submission_id)
            LEFT OUTER JOIN submission_link l ON (n.doc_id = l.doc_id AND n.span = l.span AND n.submission_id = l.submission_id)
            WHERE m.doc_id = %(doc_id)s
              AND m.submission_id = %(submission_id)s
            ORDER BY m.span
            """, doc_id=doc_id, submission_id=submission_id):
        mention = {
            "span": (row.span.lower, row.span.upper),
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": (row.canonical_span.lower, row.canonical_span.upper),
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_submission_mentions():
    doc_id = "NYT_ENG_20131216.0031"
    mentions = get_submission_mentions(1, doc_id) # patterns
    assert len(mentions) == 10
    mention = mentions[0]
    assert mention == {
        'span' : (1261, 1278),
        'gloss': 'Edward G. Rendell',
        'type': 'PER',
        'entity': {
            'span' : (1261, 1278),
            'gloss': 'Edward G. Rendell',
            'link': 'Ed_Rendell',
            },
        }

def get_evaluation_mentions(doc_id):
    """
    Get mention pairs from exhaustive mentions for a document.
    """
    mentions = []
    for row in db.select("""
            SELECT m.span, m.gloss, m.mention_type, n.span AS canonical_span, n.gloss AS canonical_gloss, l.link_name
            FROM evaluation_mention m
            JOIN evaluation_mention n ON (m.doc_id = n.doc_id AND m.canonical_span = n.span)
            LEFT OUTER JOIN evaluation_link l ON (n.doc_id = l.doc_id AND n.span = l.span)
            WHERE m.doc_id = %(doc_id)s
            ORDER BY m.span
            """, doc_id=doc_id):
        mention = {
            "span": (row.span.lower, row.span.upper),
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": (row.canonical_span.lower, row.canonical_span.upper),
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_evaluation_mentions():
    doc_id = "NYT_ENG_20130726.0208"
    mentions = get_evaluation_mentions(doc_id)
    assert len(mentions) == 118
    mention = mentions[10]
    assert mention == {
        'span': (787, 792),
        'gloss': 'Hamas',
        'type': 'ORG',
        'entity': {
            'span': (787, 792),
            'gloss': 'Hamas',
            'link': 'Hamas',
            },
        }

def get_evaluation_mention_pairs(doc_id):
    """
    Get mention pairs from exhaustive mentions for a document.
    """
    mention_pairs = set()
    for row in db.select("""
            SELECT m.span AS subject, m.mention_type AS subject_type, n.span AS object, n.mention_type AS object_type
            FROM evaluation_mention m, evaluation_mention n, sentence s
            WHERE m.doc_id = n.doc_id AND m.span <> n.span
              AND m.doc_id = s.doc_id AND m.span <@ s.span AND n.span <@ s.span
              AND m.doc_id = %(doc_id)s
              AND is_entity_type(m.mention_type)
            ORDER BY subject, object
            """, doc_id=doc_id):
        # Pick up any subject pairs that are of compatible types.
        if (row.subject_type, row.object_type) not in defs.VALID_MENTION_TYPES: continue
        # Check that this pair doesn't already exist.
        if (row.object, row.subject) in mention_pairs: continue
        mention_pairs.add((row.subject, row.object))
    return [{"subject": (subject.lower, subject.upper), "object": (object_.lower, object_.upper)} for subject, object_ in sorted(mention_pairs)]

def test_get_evaluation_mention_pairs():
    doc_id = "NYT_ENG_20130726.0208"
    pairs = get_evaluation_mention_pairs(doc_id)
    assert len(pairs) == 238
    pair = pairs[5]
    assert pair['subject'] == (628, 642)
    assert pair['object'] == (568, 574)

def get_submissions(corpus_tag):
    return db.select("""SELECT * FROM submission WHERE corpus_tag=%(corpus_tag)s ORDER BY id""", corpus_tag=corpus_tag)

def test_get_submissions():
    tag = 'kbp2016'
    assert [s.name for s in get_submissions(tag)] == ["patterns", "supervised", "rnn"]

def get_submission(submission_id):
    return next(db.select("""SELECT * FROM submission WHERE id=%(submission_id)s""", submission_id=submission_id))

def test_get_submission():
    submission_id = 1
    submission = get_submission(submission_id)
    assert submission.name == "patterns"
    assert submission.corpus_tag == "kbp2016"

def get_submission_relations(doc_id, submission_id):
    """
    Get suggested mentions for a document.
    """
    relations = []
    for row in db.select("""
            SELECT subject, relation, object, provenances, confidence
            FROM submission_relation
            WHERE doc_id = %(doc_id)s
              AND submission_id = %(submission_id)s
            ORDER BY subject
            """, doc_id=doc_id, submission_id=submission_id):
        assert len(row.provenances) > 0, "Invalid submission entry does not have any provenances"
        relation = {
            "subject": (row.subject.lower, row.subject.upper),
            "relation": row.relation,
            "object": (row.object.lower, row.object.upper),
            "provenance": (row.provenances[0].lower, row.provenances[0].upper), # Only use the first provenance.
            "confidence": row.confidence,
            }
        relations.append(relation)
    return relations

def test_get_submission_relations():
    doc_id = "NYT_ENG_20131216.0031"
    relations = get_submission_relations(doc_id, 1)
    assert len(relations) == 5
    relation = relations[0]

    assert relation == {
        "subject": (1261,1278),
        "relation": 'per:title',
        "object": (1300,1308),
        "provenance": (1196, 1338),
        "confidence": 1.
        }

def insert_evaluation_question(batch_id, params, cur=None):
    if cur is None:
        with db.CONN:
            with db.CONN.cursor() as cur:
                return insert_evaluation_question(batch_id, params, cur)
    else:
        params_str = json.dumps(params)
        id_ = sha1(params_str.encode("utf-8")).hexdigest()
        cur.execute(
            """INSERT INTO evaluation_question(id, batch_id, params) VALUES %s""",
            [(id_, batch_id, params_str)]
            )

def test_insert_evaluation_question():
    # TODO: Create a test database for this.
    raise NotImplementedError()

def insert_evaluation_batch(corpus_tag, batch_type, description, questions, cur=None):
    """
    Creates an evaluation batch with a set of questions.
    @questions is a list of parameters to launch tasks with.
    """
    if cur is None:
        with db.CONN:
            with db.CONN.cursor() as cur:
                return insert_evaluation_batch(corpus_tag, batch_type, description, questions, cur)
    else:
        # Create new batch.
        cur.execute("""
            INSERT INTO evaluation_batch(corpus_tag, batch_type, description) VALUES %s
            RETURNING (id);
            """, [(corpus_tag, batch_type, description)])
        batch_id, = next(cur)
        db.execute_values(
            cur,
            """INSERT INTO evaluation_question(id, batch_id, params) VALUES %s""",
            [(sha1(json.dumps(params).encode("utf-8")).hexdigest(), batch_id, json.dumps(params)) for params in questions])
        return batch_id

def test_insert_evaluation_batch():
    # TODO: Create a test database for this.
    raise NotImplementedError()

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
        return db.select("""SELECT * FROM mturk_hit ORDER BY id""")
    else:
        return db.select("""SELECT * FROM mturk_hit ORDER BY id LIMIT %(limit)s""", limit=limit)

def get_hit(hit_id):
    return next(db.select("""SELECT * FROM mturk_hit WHERE hit_id=%(hit_id)s""", hit_id=hit_id))

def get_task_params(hit_id):
    return next(db.select("""
        SELECT params 
        FROM mturk_hit h 
        JOIN evaluation_question q ON (h.question_batch_id = q.batch_id AND h.question_id = q.id)
        WHERE h.id=%(hit_id)s""", hit_id=hit_id)).params

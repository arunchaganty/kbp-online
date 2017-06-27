"""
Utilities connecting the web interface to database
Interfacing with database API
"""
import logging
from datetime import date, datetime
from collections import Counter

from . import db
from . import defs

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    for i, row in enumerate(db.select("""
            SELECT m.span, m.gloss, m.mention_type, n.span AS canonical_span, n.gloss AS canonical_gloss, l.link_name
            FROM evaluation_mention m
            JOIN evaluation_mention n ON (m.doc_id = n.doc_id AND m.canonical_span = n.span)
            LEFT OUTER JOIN evaluation_link l ON (n.doc_id = l.doc_id AND n.span = l.span)
            WHERE m.doc_id = %(doc_id)s
            ORDER BY m.span
            """, doc_id=doc_id)):
        mention = {
            "id": i,
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
        'id': 10,
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

def get_evaluation_relations(doc_id):
    """
    Get relations for a document.
    """
    relations = []
    for row in db.select("""
            SELECT r.subject, r.relation, r.object
            FROM evaluation_relation r
            WHERE r.doc_id = %(doc_id)s
            ORDER BY r.subject, r.object, r.relation
            """, doc_id=doc_id):
        relation = {
            "subject": (row.subject.lower, row.subject.upper),
            "relation": row.relation,
            "object": (row.object.lower, row.object.upper),
            }
        relations.append(relation)
    return relations

def test_get_evaluation_relations():
    doc_id = "NYT_ENG_20130726.0208"
    relations = get_evaluation_relations(doc_id)
    assert len(relations) == 42
    relation = relations[0]
    assert relation['subject'] == (172, 177)
    assert relation['object'] == (223, 228)
    assert relation['relation'] == 'per:place_of_residence'

def get_submissions(corpus_tag):
    return db.select("""SELECT * FROM submission WHERE corpus_tag=%(corpus_tag)s ORDER BY id""", corpus_tag=corpus_tag)

def test_get_submissions():
    tag = 'kbp2016'
    assert [s.name for s in get_submissions(tag)] == ["patterns", "supervised", "rnn"]

def get_submission(submission_id):
    return next(db.select("""SELECT id, updated, name, corpus_tag, details FROM submission WHERE id=%(submission_id)s""", submission_id=submission_id))

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

def get_submission_relation_list(submission_id, count=1):
    """
    Get suggested mentions for a document.
    """
    ret = []
    for row in db.select("""
            SELECT r.doc_id, subject, m.mention_type AS subject_type, relation, object, n.mention_type AS object_type, provenances, confidence
            FROM submission_relation r
            JOIN submission_mention m ON (r.doc_id = m.doc_id AND r.subject = m.span)
            JOIN submission_mention n ON (r.doc_id = n.doc_id AND r.object = n.span)
            WHERE r.submission_id = %(submission_id)s
            ORDER BY subject
            """, submission_id=submission_id):
        assert len(row.provenances) > 0, "Invalid submission entry does not have any provenances"

        subject, _, relation, object_, _ = defs.standardize_relation(
            row.subject, row.subject_type, row.relation, row.object, row.object_type)

        relation = {
            "doc_id": row.doc_id,
            "subject": (subject.lower, subject.upper),
            "relation": relation,
            "object": (object_.lower, object_.upper),
            "provenance": (row.provenances[0].lower, row.provenances[0].upper), # Only use the first provenance.
            "confidence": row.confidence,
            }
        ret.append(relation)

        if len(ret) == count: break
    return ret

def insert_assignment(
        assignment_id, hit_id, worker_id,
        worker_time, comments, response,
        status="Submitted", created=datetime.now()):
    batch_id = next(db.select("""SELECT batch_id FROM mturk_hit WHERE id = %(hit_id)s;""", hit_id=hit_id))

    with db.CONN:
        with db.CONN.cursor() as cur:
            db.execute("""
                INSERT INTO mturk_assignment (id, hit_id, batch_id, worker_id, created, worker_time, response, comments, status) RETURNING (id)
                VALUES (%(assignment_id)s, %(hit_id)s, %(batch_id)s, %(worker_id)s, %(created)s, %(worker_time)s, %(response)s, %(comments)s, %(status)s)""",
                       cur=cur,
                       assignment_id=assignment_id,
                       hit_id=hit_id,
                       batch_id=batch_id,
                       worker_id= worker_id,
                       created= created,
                       worker_time=int(float(worker_time)),
                       response=response,
                       comments=comments,
                       status=status)
            return next(cur).id

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

def get_submission_entries(submission_id):
    """
    Get entries from a submission that have been evaluated by Turk.
    """
    entries = []
    for i, row in enumerate(db.select("""
        SELECT doc_id,
               title,
               corpus_tag,
               sentence,
               sentence_span,
               subject_span,
               subject_type,
               subject_gloss,
               subject_link,
               subject_link_gold,
               subject_link_correct,
               subject_correct,
               object_span,
               object_type,
               object_gloss,
               object_link,
               object_link_gold,
               object_link_correct,
               object_correct,
               predicate_name,
               predicate_gold
        FROM submission_entries
        WHERE submission_id = %(submission_id)s
        ORDER BY doc_id, subject_span, object_span
        """, submission_id=submission_id)):
        entry = {
            "id": i,
            "doc_id": row.doc_id,
            "corpus_tag": row.corpus_tag,
            "title": row.title,
            "sentence": row.sentence,
            "subject": {
                "span": [row.subject_span.lower - row.sentence_span.lower, row.subject_span.upper  - row.sentence_span.lower],
                "mentionType": row.subject_type,
                "canonicalGloss": row.subject_gloss,
                "canonicalCorrect": row.subject_correct,
                "linkName": row.subject_link,
                "linkNameGold": row.subject_link_gold,
                "linkCorrect": row.subject_link_correct,
                "isCorrect": row.subject_correct and row.subject_link_correct,
                },
            "object": {
                "span": [row.object_span.lower - row.sentence_span.lower, row.object_span.upper - row.sentence_span.lower],
                "mentionType": row.object_type,
                "canonicalGloss": row.object_gloss,
                "canonicalCorrect": row.object_correct,
                "linkName": row.object_link,
                "linkNameGold": row.object_link_gold,
                "linkCorrect": row.object_link_correct,
                "isCorrect": row.object_correct and row.object_link_correct,
                },
            "predicate": {
                "name": row.predicate_name,
                "gold": row.predicate_gold,
                "isCorrect": row.predicate_name == row.predicate_gold,
                }
            }
        entries.append(entry)
    return entries

def test_get_submission_entries():
    submission_id=1
    entries = get_submission_entries(submission_id)
    assert len(entries) == 1104
    entry = entries[0]
    assert entry == {
        "id": 0,
        "sentence": "Argentine striker Barcos re-signs with Palmeiras",
        "subject": {
            "span": [119, 125],
            "mentionType": "PER",
            "canonicalGloss": "Barcos",
            "linkName": "Hernán_Barcos",
            "linkNameGold": "Hern%C3%A1n_Barcos",
            "isCorrect": False,
            },
        "object": {
            "span": [111, 118],
            "mentionType": "TITLE",
            "canonicalGloss": "striker",
            "linkName": "Striker",
            "linkNameGold": None,
            "isCorrect": True,
            },
        "predicate": {
            "name": "per:title",
            "gold": "per:title",
            "isCorrect": True,
            }
        }

def get_leaderboard():
    """Get scores for all submissions"""
    entries = []
    for row in db.select("""
        WITH latest_scores AS (SELECT DISTINCT ON (submission_id)
            submission_id, score, left_interval, right_interval
            FROM submission_score
            ORDER BY submission_id, updated DESC)
        SELECT 
        sub.id, 
        sub.updated, 
        sub.name, 
        sub.corpus_tag, 
        sub.details, 
        sc.score,
        sc.left_interval,
        sc.right_interval 
        FROM latest_scores AS sc 
        JOIN submission AS sub ON sub.id = sc.submission_id 
        ORDER BY (sc.score).f1 DESC;"""):
        entry = {
            'id': row.id,
            'name': row.name,
            'details': row.details,
            'timestamp': row.updated,
            'corpus': row.corpus_tag,
            'P': row.score.precision, 'R': row.score.recall, 'F1': row.score.f1,
            'P-range': [row.left_interval.precision, row.right_interval.precision],
            'R-range': [row.left_interval.recall, row.right_interval.recall],
            'F1-range': [row.left_interval.f1, row.right_interval.f1],
            }
        entries.append(entry)
    return {'submissions': entries}

def test_get_leaderboard():
    obj = get_leaderboard()
    assert len(obj) > 0

def get_corpus_listing(corpus_tag):
    """
    List documents from the corpus, with summaries of #entities,
    #relations.
    """
    entries = []
    for row in db.select("""
        WITH entity_counts AS (
            SELECT t.doc_id, COUNT(*)
            FROM document_tag t,
                 evaluation_mention m
            WHERE m.doc_id = t.doc_id
              AND t.tag = %(corpus_tag)s
              GROUP BY t.doc_id),
             relation_counts AS (
            SELECT t.doc_id, COUNT(*)
            FROM document_tag t,
                 evaluation_relation r
            WHERE r.doc_id = t.doc_id
              AND t.tag = %(corpus_tag)s
              GROUP BY t.doc_id)
        SELECT d.id, d.title, d.doc_date, e.count AS entity_count, r.count AS relation_count
        FROM document d
        JOIN document_tag t ON (d.id = t.doc_id AND t.tag = %(corpus_tag)s)
        JOIN entity_counts e ON (d.id = e.doc_id)
        JOIN relation_counts r ON (d.id = r.doc_id)
        ORDER BY e.count DESC, r.count DESC, d.id
        """, corpus_tag=corpus_tag):
        entry = {
            "docId": row.id,
            "title": row.title,
            "date": row.doc_date,
            "entityCount": row.entity_count,
            "relationCount": row.relation_count,
            }
        entries.append(entry)
    return entries

def test_get_corpus_listing():
    corpus_tag='kbp2016'
    entries = get_corpus_listing(corpus_tag)
    assert len(entries) == 1232
    entry = entries[0]
    assert entry == {
        'docId': 'ENG_NW_001278_20130316_F00012OME',
        'title': "3rd LD Writethru-Xinhua Insight: China's new leadership takes shape amid high expectations",
        "date": date(2013, 3, 16),
        "entityCount": 72,
        "relationCount": 119,
        }

def upload_submission(submission_id, mfile):
    with db.CONN:
        with db.CONN.cursor() as cur:
            # Create the submission
            mentions, links, relations = [], [], []

            def _p(prov):
                return db.Int4NumericRange(prov.begin, prov.end)


            for mention_id in mfile.mention_ids:
                mention_type, gloss, canonical_id = mfile.get_type(mention_id), mfile.get_gloss(mention_id), mfile.get_cmention(mention_id)
                mention_id, canonical_id = mention_id, canonical_id
                doc_id = mention_id.doc_id
                mentions.append((submission_id, doc_id, _p(mention_id), _p(canonical_id), mention_type, gloss))
            for row in mfile.links:
                mention_id = row.subj
                doc_id = mention_id.doc_id
                link_name = row.obj
                weight = row.weight
                links.append((submission_id, doc_id, _p(mention_id), link_name, weight))
            for row in mfile.relations:
                subject_id = row.subj
                object_id = row.obj
                doc_id = subject_id.doc_id

                relation = row.reln
                provs = list(row.prov) if row.prov else []
                weight = row.weight
                relations.append((submission_id, doc_id, _p(subject_id), _p(object_id), relation, [_p(prov) for prov in provs], weight))

            # mentions
            db.execute_values(cur, """INSERT INTO submission_mention (submission_id, doc_id, span, canonical_span, mention_type, gloss) VALUES %s """, mentions)

            # links
            db.execute_values(cur, """INSERT INTO submission_link (submission_id, doc_id, span, link_name, confidence) VALUES %s """, links)

            # relations
            db.execute_values(cur, """INSERT INTO submission_relation (submission_id, doc_id, subject, object, relation, provenances, confidence) VALUES %s """, relations)

            # refresh materialized views.
            cur.execute("""REFRESH MATERIALIZED VIEW submission_entity_relation""")
            cur.execute("""REFRESH MATERIALIZED VIEW submission_statistics""")
            cur.execute("""REFRESH MATERIALIZED VIEW submission_entries""")

def get_question_batch(question_batch_id):
    return db.get("""
        SELECT id, created, batch_type, corpus_tag, description FROM evaluation_batch
        WHERE id = %(batch_id)s
        """, batch_id=question_batch_id)

def get_questions(question_batch_id):
    return list(db.select("""
        SELECT id, params from evaluation_question
        WHERE batch_id = %(batch_id)s
        ORDER BY id
        """, batch_id=question_batch_id))

def get_submission_sample_batches(submission_id):
    return [row.id for row in db.select("""
        SELECT b.id
        FROM sample_batch b
        WHERE submission_id = %(submission_id)s
        ORDER BY created DESC
        """, submission_id=submission_id)]

def get_samples(sample_batch_id):
    return list(db.select("""
        SELECT submission_id, doc_id, subject, object
        FROM submission_sample
        WHERE batch_id = %(batch_id)s
        """, batch_id=sample_batch_id))

def get_evaluation_batch_status(batch_id):
    # Get's the summary of states of its questions
    stats = list(db.select("""
        SELECT state, COUNT(*) AS count
        FROM evaluation_question
        WHERE batch_id=%(batch_id)s
        GROUP BY state
        """, batch_id=batch_id))
    return Counter({state: count for state, count in stats})

def get_evaluation_batch(batch_id):
    return next(db.select("""
        SELECT id, corpus_tag, batch_type, description
        FROM evaluation_batch
        WHERE id=%(batch_id)s
        """, batch_id=batch_id))

def get_mturk_batch_status(batch_id):
    # Get's the summary of states of its questions
    stats = list(db.select("""
        SELECT state, COUNT(*) AS count
        FROM mturk_hit
        WHERE batch_id=%(batch_id)s
        GROUP BY state
        """, batch_id=batch_id))
    return Counter({state: count for state, count in stats})

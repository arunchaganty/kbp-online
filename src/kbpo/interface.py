"""
Utilities connecting the web interface to database
"""
import pdb
import unittest
from datetime import date

from . import db
from . import defs

def constructMentionPairs(doc_id):
    """
    Construct mention pairs from a given @doc_id
    """
    raise NotImplementedError

class TestInterfaceMethods(unittest.TestCase):
    """
    Test suite for methods in interface module
    """
    def constructMentionPairs_reference(self, mentions, sentences):
        """Reference implementation for creating mention pairs"""

        pairs = []
        sentence_spans = [(s[0]['doc_char_begin'], s[-1]['doc_char_end']) for s in sentences]
        sentence_to_mention_map = defaultdict(list)
        for mention in mentions:
            found = False
            for sid, span in enumerate(sentence_spans):
                if span[0]<=mention['doc_char_begin'] and span[1]>=mention['doc_char_end']:
                    sentence_to_mention_map[sid].append(mention)
                    found = True
                    break
            if not found:
                assert False
                #print "[Warning] No sentence found for mention: "+str(mention)#+"; first sentence "+str(doc['sentences'][0])
        for sid, s in sentence_to_mention_map.iteritems():
            candidates = filter(isRelationCandidate, itertools.permutations(s, 2))
            temp_map = set()
            unique_candidates = []
            #Sentence ordering is preserved while generating permutations. We assume that json code has done the same
            for c in candidates:
                fs = frozenset([mentionSpan(c[0]), mentionSpan(c[1])])
                if fs not in temp_map:
                    unique_candidates.append(c)
                    temp_map.add(fs)
            
            pairs.extend(unique_candidates)
        return pairs

    def test_constructMentionPairs(self):
        """
        Tests the construction to make sure it aligns with the previously used function
        """
        sentences = db.query_doc('NYT_ENG_20131221.0115', sentence_table = 'kbpo.sentence')
        mentions = db.query_mentions('NYT_ENG_20131221.0115', sentence_table = 'kbpo.mention')
        print(constructMentionPairs_reference(mentions, sentences))
        return 

def get_document(doc_id):
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
              AND is_entity_type(m.mention_type)
            ORDER BY m.id, subject_id, object_id
            """, doc_id=doc_id):

        pdb.set_trace()
        # Pick up any subject pairs that are of compatible types.
        if (row.subject_type, row.object_type) not in defs.VALID_MENTION_TYPES: continue
        # Check that this pair doesn't already exist.
        if (row.object_id, row.subject_id) in mention_pairs: continue
        mention_pairs.add((row.subject_id, row.object_id))
    return [{"subject_id": subject_id, "object_id": object_id} for subject_id, object_id in mention_pairs]

def test_get_suggested_mention_pairs():
    doc_id = "NYT_ENG_20131216.0031"
    pairs = get_suggested_mention_pairs(doc_id)
    assert False
    assert len(pairs) == 91

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

if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3 # -*- coding: utf-8 -*-
"""
Utilities to handle conversion and interaction of data in JSON
"""
import json
import logging
from collections import Counter, defaultdict, namedtuple
from psycopg2.extras import NumericRange
import math
import numpy as np

import datetime
from tqdm import tqdm
import urllib.parse
urllib.parse.unquote('Hern%C3%A1n_Barcos')

from . import db
from .schema import Provenance, MentionInstance, LinkInstance, RelationInstance, EvaluationMentionResponse, EvaluationLinkResponse, EvaluationRelationResponse, getNumericRange

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def parse_selective_relations_response(question, responses):
    mentions, links, relations = [], [], []
    for response in responses:
        doc_id = question["doc_id"]
        #subject_id = Provenance(doc_id, response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])

        try:
            subject_span = getNumericRange(response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])
        except IndexError as e:
            logger.error("Incorrect span for conversion to NumericRange [%d, %d)", e.args[0], e.args[1])
            continue
        
        #subject_canonical_id = Provenance(doc_id, response["subject"]["entity"]["doc_char_begin"], response["subject"]["entity"]["doc_char_end"])
        try:
            subject_canonical_span = getNumericRange(response["subject"]["entity"]["doc_char_begin"], response["subject"]["entity"]["doc_char_end"])
        except IndexError as e:
            logger.error("Incorrect span for conversion to NumericRange [%d, %d)", e.args[0], e.args[1])
            continue
        subject_type = response["subject"]["type"]["name"].strip()
        subject_gloss = response["subject"]["gloss"].strip()

        #object_id = Provenance(doc_id, response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        try:
            object_span = getNumericRange(response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        except IndexError as e:
            logger.error("Incorrect span for conversion to NumericRange [%d, %d)", e.args[0], e.args[1])
            continue


        #object_canonical_id = Provenance(doc_id, response["object"]["entity"]["doc_char_begin"], response["object"]["entity"]["doc_char_end"])
        try:
            object_canonical_span = getNumericRange(response["object"]["entity"]["doc_char_begin"], response["object"]["entity"]["doc_char_end"])
        except IndexError as e:
            logger.error("Incorrect span for conversion to NumericRange [%d, %d})", e.args[0], e.args[1])
            continue

        object_type = response["object"]["type"]["name"].strip()
        object_gloss = response["object"]["gloss"].strip()

        assert "canonicalCorrect" in response["subject"]["entity"]
        if "canonicalCorrect" in response["subject"]["entity"]:
            mentions.append(MentionInstance(doc_id, subject_span, subject_canonical_span, subject_type, subject_gloss, 1.0 if response["subject"]["entity"]["canonicalCorrect"] == "Yes" else 0.0))
        if "canonicalCorrect" in response["object"]["entity"]:
            mentions.append(MentionInstance(doc_id, object_span, object_canonical_span, object_type, object_gloss, 1.0 if response["object"]["entity"]["canonicalCorrect"] == "Yes" else 0.0))
        if "linkCorrect" in response["subject"]["entity"]:
            links.append(LinkInstance(doc_id, subject_span, urllib.parse.unquote(response["subject"]["entity"]["link"]), 1.0 if response["subject"]["entity"]["linkCorrect"] == "Yes" else 0.0))
        if "linkCorrect" in response["object"]["entity"]:
            links.append(LinkInstance(doc_id, object_span, urllib.parse.unquote(response["object"]["entity"]["link"]), 1.0 if response["object"]["entity"]["linkCorrect"] == "Yes" else 0.0))

        relations.append(RelationInstance(doc_id, subject_span, object_span, response["relation"], 1.0))
    return sorted(set(mentions)), sorted(set(links)), sorted(set(relations))

def test_parse_selective_relations_response():
    # My output could be one of the following cases
    # - the mention could be wrong. (TODO: how are we handling this?)
    # - the linking could be wrong.
    # - the relation could be wrong.
    question = {"mention_2": ["NYT_ENG_20130911.0085", "2803", "2809"], "doc_id": "NYT_ENG_20130911.0085", "batch_type": "selective_relations", "mention_1": ["NYT_ENG_20130911.0085", "2778", "2783"]}
    response = {"subject":{"gloss":"Mukesh","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":2803,"doc_char_end":2809,"entity":{"gloss":"Mukesh","link":"Mukesh_Ambani","doc_char_begin":2803,"doc_char_end":2809,"canonicalCorrect":"Yes","linkCorrect":"No"}},"relation":"per:sibling","object":{"gloss":"Singh","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":2778,"doc_char_end":2783,"entity":{"gloss":"Ram Singh","link":"Ram_Singh","doc_char_begin":1703,"doc_char_end":1712,"canonicalCorrect":"Yes","linkCorrect":"No"}}}
    subject_id = Provenance('NYT_ENG_20130911.0085', 2803, 2809)
    subject_canonical_id = Provenance('NYT_ENG_20130911.0085', 2803, 2809)
    object_id = Provenance('NYT_ENG_20130911.0085', 2778, 2783)
    object_canonical_id = Provenance('NYT_ENG_20130911.0085', 1703, 1712)

    mentions_, links_, relations_ = parse_selective_relations_response(question, response)
    assert mentions_ == [MentionInstance(subject_id, subject_canonical_id, 'PER', 'Mukesh', 1.0), MentionInstance(object_id, object_canonical_id, 'PER', 'Singh', 1.0)]
    assert links_ == [LinkInstance(subject_id, "Mukesh_Ambani", 0.0), LinkInstance(object_id, "Ram_Singh", 0.0)]
    assert relations_ == [RelationInstance(subject_id, object_id, "per:sibling", 1.0)]

def parse_exhaustive_relations_response(question, responses):
    mentions, links, relations = [], [], []
    doc_id = question["doc_id"]
    for response in responses:
        #subject = Provenance(doc_id, response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])
        try:
            subject_span = getNumericRange(response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])
        except IndexError as e:
            logger.error("Incorrect span for conversion to NumericRange [%d, %d)", e.args[0], e.args[1])
            continue

        #object_ = Provenance(doc_id, response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        try:
            object_span = getNumericRange(response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        except IndexError as e:
            logger.error("Incorrect span for conversion to NumericRange [%d, %d)", e.args[0], e.args[1])
            continue
        relation = RelationInstance(doc_id, subject_span, object_span, response["relation"], 1.0)
        relations.append(relation)
    return sorted(set(mentions)), sorted(set(links)), sorted(set(relations))

def test_parse_exhaustive_relations_response():
    question = {"doc_id": "ENG_NW_001278_20130216_F00011Q88", "batch_type": "exhaustive_relations"}
    response = [{"subject":{"gloss":"\xa0Ahmed\xa0Omar","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":438,"doc_char_end":448,"entity":{"gloss":"\xa0Ahmed\xa0Omar","link":"","doc_char_begin":438,"doc_char_end":448}},"relation":"per:employee_or_member_of","object":{"gloss":"\xa0Health\xa0Ministry","type":{"idx":1,"name":"ORG","gloss":"Organization","icon":"fa-building","linking":"wiki-search"},"doc_char_begin":412,"doc_char_end":427,"entity":{"gloss":"\xa0Health\xa0Ministry","link":"Ministry_of_Health_(Egypt)","doc_char_begin":412,"doc_char_end":427}}},{"subject":{"gloss":"\xa0al-Jamaa\xa0al-\xa0Islamiya","type":{"idx":1,"name":"ORG","gloss":"Organization","icon":"fa-building","linking":"wiki-search"},"doc_char_begin":983,"doc_char_end":1004,"entity":{"gloss":"\xa0al-Jamaa\xa0al-\xa0Islamiya","link":"Al-Jama%27a_al-Islamiyya","doc_char_begin":983,"doc_char_end":1004}},"relation":"org:member_of","object":{"gloss":"\xa0Construction\xa0and\xa0Development\xa0Party","type":{"idx":1,"name":"ORG","gloss":"Organization","icon":"fa-building","linking":"wiki-search"},"doc_char_begin":1031,"doc_char_end":1065,"entity":{"gloss":"\xa0Construction\xa0and\xa0Development\xa0Party","link":"Building_and_Development_Party","doc_char_begin":1031,"doc_char_end":1065}}},{"subject":{"gloss":"\xa0Mohamed","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":1229,"doc_char_end":1236,"entity":{"gloss":"\xa0Mohamed","link":"Mohamed_Morsi","doc_char_begin":1229,"doc_char_end":1236}},"relation":"per:title","object":{"gloss":"\xa0President","type":{"idx":4,"name":"TITLE","gloss":"Title","icon":"fa-id-card-o","linking":""},"doc_char_begin":1219,"doc_char_end":1228,"entity":{"gloss":"\xa0President","link":"","doc_char_begin":1219,"doc_char_end":1228}}},{"subject":{"gloss":"\xa0Morsi","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":1237,"doc_char_end":1242,"entity":{"gloss":"\xa0Mohamed","link":"Mohamed_Morsi","doc_char_begin":1229,"doc_char_end":1236}},"relation":"per:title","object":{"gloss":"\xa0President","type":{"idx":4,"name":"TITLE","gloss":"Title","icon":"fa-id-card-o","linking":""},"doc_char_begin":1219,"doc_char_end":1228,"entity":{"gloss":"\xa0President","link":"","doc_char_begin":1219,"doc_char_end":1228}}}]

    mentions, links, relations = parse_exhaustive_relations_response(question, response)
    assert len(mentions) == 0
    assert len(links) == 0
    assert len(relations) == 4
    assert relations[0].subject_id == Provenance("ENG_NW_001278_20130216_F00011Q88", 438, 448)
    assert relations[0].object_id == Provenance("ENG_NW_001278_20130216_F00011Q88", 412, 427)
    assert relations[0].relation == "per:employee_or_member_of"

def parse_exhaustive_entities_response(question, response):
    doc_id = question["doc_id"]
    mentions = []
    links = []
    relations = []
    for entity in response:
        try:
            #id_ = Provenance(doc_id,entity["doc_char_begin"], entity["doc_char_end"]) 
            try:
                span = getNumericRange(entity["doc_char_begin"], entity["doc_char_end"])
            except IndexError as e:
                logger.error("Incorrect span for conversion to NumericRange [%d, %d)", e.args[0], e.args[1])
                continue
            
            type_ = entity["type"]["name"].strip()
            gloss = entity["gloss"].strip()

            #canonical_id = Provenance(doc_id, entity["entity"]["doc_char_begin"], entity["entity"]["doc_char_end"])
            try:
                canonical_span = getNumericRange(entity["entity"]["doc_char_begin"], entity["entity"]["doc_char_end"])
            except IndexError as e:
                logger.error("Incorrect span for conversion to NumericRange [%d, %d)", e.args[0], e.args[1])
                continue
            mention = MentionInstance(doc_id, span, canonical_span, type_, gloss, 1.0)
            mentions.append(mention)

            if span == canonical_span:
                link = LinkInstance(doc_id, span, urllib.parse.unquote(entity["entity"]["link"]), 1.0)
                links.append(link)
        except AssertionError as e:
            logger.error("Could not process response {}: {}".format(entity, e))

    return sorted(set(mentions)), sorted(set(links)), sorted(set(relations))

def test_parse_exhaustive_entities_response():
    question = {"doc_id": "NYT_ENG_20130911.0085", "batch_type": "exhaustive_entities"}
    response = [{"gloss": "China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 106, "doc_char_begin": 101, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 212, "doc_char_begin": 207, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 308, "doc_char_begin": 303, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 524, "doc_char_begin": 519, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 896, "doc_char_begin": 891, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 1232, "doc_char_begin": 1227, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 1308, "doc_char_begin": 1303, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "BEIJING", "entity": {"gloss": "BEIJING", "doc_char_end": 282, "link": "Beijing", "doc_char_begin": 275}, "doc_char_end": 282, "doc_char_begin": 275, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0May\u00a015", "entity": {"gloss": "\u00a0May\u00a015", "doc_char_end": 290, "link": "2001-05-15", "doc_char_begin": 284}, "doc_char_end": 290, "doc_char_begin": 284, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "Xinhua", "entity": {"gloss": "Xinhua", "doc_char_end": 298, "link": "Xinhua_News_Agency", "doc_char_begin": 292}, "doc_char_end": 298, "doc_char_begin": 292, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "entity": {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "doc_char_end": 338, "link": "Ministry_of_Public_Security_(China)", "doc_char_begin": 311}, "doc_char_end": 338, "doc_char_begin": 311, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0MPS", "entity": {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "doc_char_end": 338, "link": "Ministry_of_Public_Security_(China)", "doc_char_begin": 311}, "doc_char_end": 459, "doc_char_begin": 456, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0MPS", "entity": {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "doc_char_end": 338, "link": "Ministry_of_Public_Security_(China)", "doc_char_begin": 311}, "doc_char_end": 788, "doc_char_begin": 785, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0Police\u00a0Force\u00a0of\u00a0Myanmar", "entity": {"gloss": "\u00a0Police\u00a0Force\u00a0of\u00a0Myanmar", "doc_char_end": 376, "link": "", "doc_char_begin": 353}, "doc_char_end": 376, "doc_char_begin": 353, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0Nansan-Lougai", "entity": {"gloss": "\u00a0Nansan-Lougai", "doc_char_end": 495, "link": "", "doc_char_begin": 482}, "doc_char_end": 495, "doc_char_begin": 482, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan\u00a0Province", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 542, "doc_char_begin": 527, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 709, "doc_char_begin": 703, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Kokang", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 572, "doc_char_begin": 566, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 1220, "doc_char_begin": 1214, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 1431, "doc_char_begin": 1425, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Ruili", "entity": {"gloss": "\u00a0Ruili", "doc_char_end": 717, "link": "Ruili", "doc_char_begin": 712}, "doc_char_end": 717, "doc_char_begin": 712, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Longchuan", "entity": {"gloss": "\u00a0Longchuan", "doc_char_end": 731, "link": "Longchuan", "doc_char_begin": 722}, "doc_char_end": 731, "doc_char_begin": 722, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a02007", "entity": {"gloss": "\u00a02007", "doc_char_end": 755, "link": "2007-12-XX", "doc_char_begin": 751}, "doc_char_end": 755, "doc_char_begin": 751, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "\u00a02008", "entity": {"gloss": "\u00a02008", "doc_char_end": 764, "link": "2008-12-XX", "doc_char_begin": 760}, "doc_char_end": 764, "doc_char_begin": 760, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "\u00a0April\u00a02009", "entity": {"gloss": "\u00a0April\u00a02009", "doc_char_end": 1300, "link": "2009-04-01", "doc_char_begin": 1290}, "doc_char_end": 1300, "doc_char_begin": 1290, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "\u00a0Vietnam", "entity": {"gloss": "\u00a0Vietnam", "doc_char_end": 1412, "link": "Vietnam", "doc_char_begin": 1405}, "doc_char_end": 1412, "doc_char_begin": 1405, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Laos", "entity": {"gloss": "\u00a0Laos", "doc_char_end": 1421, "link": "Laos", "doc_char_begin": 1417}, "doc_char_end": 1421, "doc_char_begin": 1417, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Guangxi\u00a0Zhuang\u00a0Autonomous\u00a0Region", "entity": {"gloss": "\u00a0Guangxi\u00a0Zhuang\u00a0Autonomous\u00a0Region", "doc_char_end": 1468, "link": "Guangxi", "doc_char_begin": 1436}, "doc_char_end": 1468, "doc_char_begin": 1436, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}]
    #"
    mentions, links, relations = parse_exhaustive_entities_response(question, response)

    assert len(mentions) == 28
    assert len(links) == 16
    assert len(relations) == 0

    assert mentions[0].id == Provenance("NYT_ENG_20130911.0085", 101, 106)
    assert mentions[0].canonical_id == Provenance("NYT_ENG_20130911.0085", 101, 106)
    assert mentions[0].type == "GPE"
    assert mentions[0].gloss == "China"
    assert links[0].id == Provenance("NYT_ENG_20130911.0085", 101, 106)
    assert links[0].link_name == "China"

def parse_responses():
# TODO: Include some awareness of timestamps
    evaluation_mentions = []
    evaluation_links = []
    evaluation_relations = []

    rows = db.select("""
SELECT a.id AS assignment_id, b.id AS question_batch_id, q.id AS question_id, b.batch_type, q.params AS question, a.response AS response
FROM mturk_assignment a,
     mturk_hit h,
     evaluation_question q,
     evaluation_batch b
WHERE a.hit_id = h.id AND h.question_id = q.id AND h.question_batch_id = q.batch_id AND b.id = q.batch_id
 AND NOT a.ignored""")

    for row in tqdm(rows): # Q: Should there be a fixed type?
        if len(row.response) == 0:
            logger.warning("Empty response : %s", row)
            continue

        question = row.question
        response = row.response

        if row.batch_type == "selective_relations":
            mentions, links, relations = parse_selective_relations_response(question, response)
        elif row.batch_type == "exhaustive_relations":
            mentions, links, relations = parse_exhaustive_relations_response(question, response)
        elif row.batch_type == "exhaustive_entities":
            mentions, links, relations = parse_exhaustive_entities_response(question, response)
        else:
            raise ValueError("Unexpected batch type: " + row.batch_type)

        #raise Exception()

        # evaluation_mention_response
        for mention in mentions:
            response = EvaluationMentionResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                mention.doc_id,
                mention.span,
                mention.canonical_span,
                mention.mention_type,
                mention.gloss,
                mention.weight,)

            assert response not in evaluation_mentions
            evaluation_mentions.append(response)

        # evaluation_link_response
        for link in links:
            evaluation_links.append(EvaluationLinkResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                link.doc_id,
                link.span,
                link.link_name,
                link.weight,))

        for relation in relations:
            evaluation_relations.append(EvaluationRelationResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                relation.doc_id,
                relation.subject,
                relation.object,
                relation.relation,
                relation.weight,))

    assert len(evaluation_mentions) == len(set(evaluation_mentions))
    assert len(evaluation_links) == len(set(evaluation_links))
    assert len(evaluation_relations) == len(set(evaluation_relations))

    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""TRUNCATE evaluation_mention_response;""")
            cur.execute("""TRUNCATE evaluation_link_response;""")
            cur.execute("""TRUNCATE evaluation_relation_response;""")
            db.execute_values(cur, """INSERT INTO evaluation_mention_response(assignment_id, question_batch_id, question_id, doc_id, span, canonical_span, mention_type, gloss, weight) VALUES %s""", evaluation_mentions)
            db.execute_values(cur, """INSERT INTO evaluation_link_response(assignment_id, question_batch_id, question_id, doc_id, span, link_name, weight) VALUES %s""", evaluation_links)
            db.execute_values(cur, """INSERT INTO evaluation_relation_response(assignment_id, question_batch_id, question_id, doc_id, subject, object, relation, weight) VALUES %s""", evaluation_relations)

def majority_element(lst):
    return Counter(lst).most_common(1)[0][0]

#def merge_evaluation_mentions(row):
#    assert len(row) > 0.
#    # Only merge eval mentions with > 1 response.
#    # Choose the most frequent char_begin and char_end.
#    #TODO: the elements in lst should be weighed by the weight of their vote (e.g. canonical_mention if wrong)
#    canonical_begin, canonical_end = majority_element([(b,e) for b,e in zip(row.canonical_char_begins, row.canonical_char_ends)])
#    mention_type = majority_element(row.mention_types)
#    gloss = majority_element(row.glosses)
#    weight = sum(weight for weight, canonical_begin_, canonical_end_ in zip(row.weights, row.canonical_char_begins, row.canonical_char_ends) if canonical_begin_ == canonical_begin and canonical_end_ == canonical_end)/len(row.weights)
#
#    return row.doc_id, row.mention_id, (row.doc_id, canonical_begin, canonical_end), mention_type, gloss, weight

def _merge_evaluation_mentions(cur, doc_table = None):
    """
    Merges evaluation_mention_responses from the documents in @doc_table
    Algorithm
        1)  Compute table span_denominator
            having denominator (number of times the question was asked)
            by getting all the questions to which this reponses is, along
            with the number of assignments in the mturk_batch for each
        2)  Compute table span_counts
            For a submitted span, its count is the number of spans which 
            contain it and have the same type. 
            This is done using a self join, which counts the number of pairs
            of spans contributing towards a single span within. Since it is 
            always a clique (easy to verify) the count can be easily recovered
        3)  Iterate through the spans to get winning_spans, i.e. set of non-
            overlapping spans with highest count and count>denominator/2
            Also compute a span_to_winning_span_map, which maps a span, to one 
            of its contained spans to the first contained winning span
        4)  Replace canonical spans with new-canonical spans based on 
            span_to_winning_span_map then take the most common winning canonical
            span
        Note: This code assumes at least 2 responses are being merged. It fails if only 1 response is supposed to be merged. 
        Note: The weights are assumed to be 0 or 1, and only those mentions with weight 1 are counted
    """

    db.execute("""
    DROP TABLE IF EXISTS span_counts;
    CREATE  TABLE span_counts AS (
        SELECT span_count.*, 0.5 + sqrt(0.25 + 2* (span_count.pair_count)) AS count, d.question_id, d.question_batch_id, d.denominator
        FROM (
            SELECT m1.doc_id, m1.span, mode() WITHIN GROUP (ORDER BY m1.gloss) AS gloss, m1.mention_type, count(*) as pair_count, array_agg(m1.canonical_span) || array_agg(m2.canonical_span) as canonical_spans
            FROM evaluation_mention_response_flat AS m1 
            JOIN """+doc_table+""" as docs ON m1.doc_id = docs.doc_id
            JOIN evaluation_mention_response AS m2 ON m1.doc_id = m2.doc_id 
                 AND (m1.span <@ m2.span OR m1.span = m2.span) 
                 AND m1.mention_type = m2.mention_type
                 AND m1.assignment_id < m2.assignment_id 
            WHERE m1.weight = 1 AND m2.weight = 1
            GROUP BY m1.doc_id, m1.span, m1.mention_type) AS span_count
            LEFT JOIN _denominator AS d 
                ON span_count.doc_id = d.doc_id AND span_count.span = d.span
        );
    """, cur)

    winning_spans = []
    span_to_winning_span_map = {}
    spans_window = []
    winning_span = None
    for span_row in tqdm(db.select("SELECT * from span_counts ORDER BY doc_id, span, count;")):
        spans_window.append(span_row)
        if winning_span is None:
            winning_span = span_row
            spans_window = [span_row]
        elif span_row.doc_id != winning_span.doc_id or span_row.span.lower >= winning_span.span.upper:
            if winning_span is not None and winning_span.count > winning_span.denominator/2.0:
                winning_spans.append(winning_span)
                for span in spans_window:
                    span_to_winning_span_map[(span.doc_id, span.span)] = (winning_span.doc_id, winning_span.span)
            else:
                for span in spans_window:
                    span_to_winning_span_map[(span.doc_id, span.span)] = None
            winning_span = span_row
            spans_window = [span_row]
        else:
            if span_row.count > span_row.denominator/2.0 and span_row.span.upper - span_row.span.lower >  winning_span.span.upper - winning_span.span.lower:
                winning_span = span_row

    _temp = winning_spans
    winning_spans = []
    for x in _temp:
        x = dict(**x._asdict())
        majority_can_span = majority_element([span_to_winning_span_map[(x['doc_id'], can_span)] if (x['doc_id'], can_span) in span_to_winning_span_map else None for can_span in x['canonical_spans']])
        if majority_can_span is None:
            x['canonical_span'] = x['span']
        else:
            x['canonical_span'] = majority_can_span[1]
        x['weight'] = x['count']/x['denominator']
        del x['canonical_spans']
        winning_spans.append(x)

    args_str = b','.join(db.mogrify("(%(doc_id)s,%(span)s,%(question_batch_id)s, %(question_id)s, %(canonical_span)s, %(mention_type)s,%(gloss)s,%(weight)s )",cur=cur, verbose=False, **x) for x in winning_spans)
    cur.execute("""DELETE FROM evaluation_mention AS m USING """+doc_table+""" AS docs WHERE m.doc_id = docs.doc_id;""")
    cur.execute(b""" 
            INSERT INTO evaluation_mention (doc_id, span, question_batch_id, question_id, canonical_span, mention_type, gloss, weight) VALUES"""
     + args_str) 
                
def _merge_evaluation_links(cur, doc_table):
    """
    Merge evaluation_link_responses to get the modal link
        Compute the winner by majority
        Does not guarantee that every evaluation mention will have a link
        Does not map to winning spans because links are highly sensitive to spans
    """
    db.execute("""DELETE FROM evaluation_link AS m USING """+doc_table+""" AS docs WHERE m.doc_id = docs.doc_id;""", cur=cur)
    db.execute(
        """
        INSERT INTO evaluation_link (doc_id, span, question_batch_id, question_id, link_name, weight)
        SELECT c.doc_id, c.span, d.question_batch_id, d.question_id, c.link_name, c.count/d.denominator as weight FROM 
            (SELECT lr.doc_id, span, link_name, sum(weight) as count
            FROM evaluation_link_response as lr
            JOIN """+doc_table+""" as docs ON lr.doc_id = docs.doc_id
            GROUP BY lr.doc_id, span, link_name) AS c
        JOIN _denominator as d
            ON d.doc_id = c.doc_id AND d.span = c.span
        WHERE c.count/d.denominator > 0.5;
        """, cur = cur)
    
def _merge_evaluation_relations(cur, doc_table):
    raise NotImplementedError

def merge_evaluation_links(row):
    assert len(row) > 0.
    link_name = majority_element(row.link_names)
    weight = sum(weight for weight, link_name_ in zip(row.weights, row.link_names) if link_name_ == link_name)/len(row.weights)

    return row.doc_id, row.mention_id, link_name, weight

def merge_evaluation_relations(row):
    assert len(row) > 0.
    # Choose the most frequent char_begin and char_end.
    relation = majority_element(row.relations)
    n_assignments = max(max([int(json.loads(params)['max_assignments']) for params in row.params]), len(row.weights))

    #param = majority_element(row.params)
    weight = sum(weight for weight, relation_ in zip(row.weights, row.relations) if relation_ == relation)/n_assignments

    return row.question_id, row.question_batch_id, row.doc_id, row.subject_id, row.object_id, relation, weight

## TODO: Fix to handle overlapping mentions, etc. -- basically this approach is broken.
#def update_evaluation_mention():
#    with db.CONN:
#        with db.CONN.cursor() as cur:
#            cur.execute("""TRUNCATE evaluation_mention;""")
#            # For evaluation_mention, we want to aggregate both types and canonical_ids.
#            # TODO: WARNING: THIS DOES NOT ACCURATELY HANDLE THE CASE
#            # WHERE A SELECTIVE ANNOTATOR IDENTIFIES A MENTION IN
#            # A DOCUMENT WITH EXHAUSTIVE ANNOTATIONS BECAUSE IT OVER
#            # COUNTS THE "TOTAL_COUNT" USED DURING MERGING.
#            cur.execute("""
#            WITH _response_count AS (SELECT doc_id, COUNT(DISTINCT assignment_id) FROM evaluation_mention_response GROUP BY doc_id)
#            SELECT r.doc_id, mention_id,
#                    array_agg(assignment_id)
#                    array_agg((canonical_id).char_begin) AS canonical_char_begins, array_agg((canonical_id).char_end) AS canonical_char_ends,
#                    array_agg(mention_type) AS mention_types, array_agg(gloss) AS glosses,
#                    array_agg(weight) AS weights,
#                    min(c.count) AS total_count
#            FROM evaluation_mention_response r
#            JOIN _response_count c ON (r.doc_id = c.doc_id)
#            GROUP BY doc_id, mention_id""")
#            # Take the majority vote on this mention iff count > 1.
#            values = [merge_evaluation_mentions(row) for row in tqdm(cur, total=cur.rowcount)]
#            logger.info("%d rows of evaluation_mention_response merged into %d rows", cur.rowcount, len(values))
#            db.execute_values(cur, """INSERT INTO evaluation_mention(doc_id, mention_id, canonical_id, mention_type, gloss, weight) VALUES %s""", values)

def merge_evaluation_table(table, mode = 'update'):
    merging_tables = {table: 'evaluation_'+table+'_response' for table in ['mention', 'link', 'relation']}
    merging_funcs = {'mention': _merge_evaluation_mentions, 'link': _merge_evaluation_links, 'relation': _merge_evaluation_relations}
    pkey_fields = {'mention': ('doc_id', 'span'), 'link': ('doc_id', 'span'), 'relation': ('doc_id', 'subject', 'object')}

    
    with db.CONN: 
        with db.CONN.cursor() as cur:
            if mode == 'all':
                cur.execute("CREATE TEMP TABLE _docids_for_merging AS (SELECT distinct doc_id FROM "+merging_tables[table]+");")
                cur.execute("CREATE INDEX docid_idx ON _docids_for_merging(doc_id);")
            #TODO: add update and doc_list modes
            db.execute("""
            DROP TABLE IF EXISTS _denominator;
            CREATE TEMP TABLE _denominator AS (
                SELECT """+','.join(pkey_fields[table])+""", array_agg(question_id) as question_id, array_cat_agg(question_batch_id) as question_batch_id, sum(n_assignments) AS denominator
                FROM (SELECT """+','.join(map(lambda x: 'm.'+x, pkey_fields[table]))+""", m.question_id, array_agg(DISTINCT m.question_batch_id) AS question_batch_id, m.batch_id, mode() WITHIN GROUP (ORDER BY m.mturk_batch_params#>>'{max_assignments}')::int as n_assignments
                    FROM evaluation_mention_response_flat AS m JOIN 
                    _docids_for_merging
                    AS docs ON m.doc_id = docs.doc_id 
                    GROUP BY """+','.join(map(lambda x: 'm.'+x, pkey_fields[table]))+""", m.batch_id, m.question_id) 
                    as temp GROUP BY """+','.join(pkey_fields[table])+"""
                );
            """, cur)
            merging_funcs[table](cur, '_docids_for_merging')


def _update_evaluation_link():
    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""TRUNCATE evaluation_link;""")
            # For evaluation_mention, we want to aggregate both types and canonical_ids.
            cur.execute("""
            WITH _response_count AS (SELECT doc_id, COUNT(DISTINCT assignment_id) FROM evaluation_mention_response GROUP BY doc_id)
            SELECT doc_id, mention_id, array_agg(link_name) AS link_names, array_agg(weight) AS weights 
            FROM evaluation_link_response GROUP BY doc_id, mention_id""")
            # Take the majority vote on this mention iff count > 1.
            values = [merge_evaluation_links(row) for row in tqdm(cur, total=cur.rowcount)]
            logger.info("%d rows of evaluation_link_response merged into %d rows", cur.rowcount, len(values))
            db.execute_values(cur, """INSERT INTO evaluation_link(doc_id, mention_id, link_name, weight) VALUES %s""", values)

def update_evaluation_relation():
    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""TRUNCATE evaluation_relation;""")
            # For evaluation_mention, we want to aggregate both types and canonical_ids.
            cur.execute("""SELECT question_id, question_batch_id, doc_id, subject_id, object_id, array_agg(relation) AS relations, array_agg(weight) as weights, array_agg(params) as params FROM evaluation_relation_response as r, mturk_assignment as a, mturk_batch as b WHERE r.assignment_id = a.id AND a.batch_id = b.id GROUP BY question_id, question_batch_id, doc_id, subject_id, object_id""")
            # Take the majority vote on this mention iff count > 1.
            values = [merge_evaluation_relations(row) for row in tqdm(cur, total=cur.rowcount)]
            logger.info("%d rows of evaluation_relation_response merged into %d rows", cur.rowcount, len(values))
            db.execute_values(cur, """INSERT INTO evaluation_relation(question_id, question_batch_id, doc_id, subject_id, object_id, relation, weight) VALUES %s""", values)

def update_summary():
    """
    Updates the evaluation_mention, evaluation_link and evaluation_relation tables.
    """
    update_evaluation_mention()
    update_evaluation_link()
    update_evaluation_relation()


    

                

"""
CREATE TEMP TABLE mention_gloss_true AS (
    SELECT m.doc_id, m.span, array_agg(w.gloss) 
    FROM (SELECT distinct doc_id, span  FROM evaluation_mention_response) as m 
    LEFT JOIN (SELECT doc_id, int4range(dcb, dce) as span, gloss FROM (
        SELECT doc_id, unnest(doc_char_begin) AS dcb, unnest(doc_char_end) AS dce, unnest(words) as gloss 
        FROM sentence ORDER BY doc_id) as t) AS w 
    ON m.doc_id = w.doc_id AND m.span @> w.span group by m.doc_id, m.span
);
"""


def sanitize_mention_response(response):
    """Sanitize mention_response given a row of responses from sanitize_evaluation_mention_response view"""
    if response.tm_gloss is None:
        return "Delete"
    gloss = response.gloss
    tm_gloss = response.tm_gloss
    if gloss == tm_gloss:
        return "Correct"
    gloss = gloss.replace('``', '"')
    tm_gloss = tm_gloss.replace(u'&amp;', '&');
    tm_gloss = tm_gloss.replace(u'&amp;', '&');
    tm_gloss = tm_gloss.replace(u'’', '\'');
    tm_gloss = tm_gloss.replace(u'“', '\"');
    #response.tm_gloss.replace(u'&amp;', '&');
    if gloss == tm_gloss:
        return "Replace gloss"

    if gloss != tm_gloss:
        #Local check for consistency
        if response.sm_gloss is not None and len(response.sm_gloss) == response.sm_span.upper - response.sm_span.lower:
            return "Replace with suggested"
        else:
            return "Replace gloss"

       #TODO: Fancier but low impact filters
       # 
       #     if len(tm_gloss) < len(gloss):
       #         pass
       #         print(("Garbled order: incorrect span length", (gloss, tm_gloss, response.sm_gloss)))
       #     elif len(tm_gloss) > len(gloss):
       #         print(("Garbled order: gloss missing words", (gloss, tm_gloss, response.sm_gloss)))
       #         pass
       #     else:
       #         pass
       #         print(("Unknown", (gloss, tm_gloss, response.sm_gloss)))
            

def test_sanitize_mention_response():
    Record = namedtuple('Record', 
            ['assignment_id', 'doc_id', 'span', 'created', 'question_batch_id', 'question_id', 'canonical_span', 'mention_type', 'gloss', 'weight', 'tm_gloss', 'sm_span', 'sm_gloss', 'sm_canonical_span'])
    test_cases = [
            [Record(assignment_id='3PJUZCGDJ7A8B8QNC7GL12PWTZK98R', doc_id='ENG_NW_001278_20130215_F000127AV', span=NumericRange(729, 741, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=3, question_id='113c9eed635cdecf6eddd9a154463cfd', canonical_span=NumericRange(729, 741, '[)'), mention_type='GPE', gloss='South and Africa', weight=1.0, tm_gloss='South Africa', sm_span=NumericRange(729, 741, '[)'), sm_gloss='South Africa', sm_canonical_span=NumericRange(729, 741, '[)')), 'Replace with suggested'], 
            [Record(assignment_id='373ERPL3YP2XDSEX9MR2JJLDD0RRT5', doc_id='NYT_ENG_20130822.0209', span=NumericRange(2367, 2380, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=7, question_id='fc12b4895369c4994df245c97886f25b', canonical_span=NumericRange(2367, 2380, '[)'), mention_type='PER', gloss='Anne McClain', weight=1.0, tm_gloss='Anne  McClain', sm_span=NumericRange(2367, 2380, '[)'), sm_gloss='Anne McClain', sm_canonical_span=NumericRange(2367, 2380, '[)')), 'Replace with suggested'], 
            [Record(assignment_id='369J354OFE40M4U7XYPX95FSRJ8G6Q', doc_id='ENG_NW_001278_20130401_F000139FI', span=NumericRange(257, 266, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=3, question_id='838cdc9750d0192283de300b7061ad1b', canonical_span=NumericRange(101, 106, '[)'), mention_type='ORG', gloss='Apple Inc.', weight=1.0, tm_gloss='Apple Inc', sm_span=NumericRange(257, 266, '[)'), sm_gloss='Apple Inc.', sm_canonical_span=NumericRange(101, 106, '[)')), 'Replace with suggested'], 
            [Record(assignment_id='373ERPL3YP2XDSEX9MR2JJLDD0RRT5', doc_id='NYT_ENG_20130822.0209', span=NumericRange(2367, 2380, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=7, question_id='fc12b4895369c4994df245c97886f25b', canonical_span=NumericRange(2367, 2380, '[)'), mention_type='PER', gloss='Anne McClain', weight=1.0, tm_gloss='Anne  McClain', sm_span=NumericRange(2367, 2380, '[)'), sm_gloss='Anne McClain', sm_canonical_span=NumericRange(2367, 2380, '[)')), 'Replace with suggested'], 
            [Record(assignment_id='369J354OFE40M4U7XYPX95FSRJ8G6Q', doc_id='ENG_NW_001278_20130401_F000139FI', span=NumericRange(257, 266, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=3, question_id='838cdc9750d0192283de300b7061ad1b', canonical_span=NumericRange(101, 106, '[)'), mention_type='ORG', gloss='Apple Inc.', weight=1.0, tm_gloss='Apple Inc', sm_span=NumericRange(257, 266, '[)'), sm_gloss='Apple Inc.', sm_canonical_span=NumericRange(101, 106, '[)')), 'Replace with suggested'], 
            [Record(assignment_id='31LVTDXBL849UF6S0DPBXSBWJLOLRB', doc_id='ENG_NW_001278_20130306_F000127H7', span=NumericRange(1339, 1347, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=3, question_id='ba537d0fc9f08201ff6db1e032590820', canonical_span=NumericRange(316, 330, '[)'), mention_type='PER', gloss='Rousseff', weight=1.0, tm_gloss='Rousseff', sm_span=NumericRange(1339, 1347, '[)'), sm_gloss='Rousseff', sm_canonical_span=NumericRange(316, 330, '[)')), 'Correct'], 
            [Record(assignment_id='3OJSZ2ATDTQLA7JSZCBYBMOZWMN577', doc_id='NYT_ENG_20131211.0211', span=NumericRange(332, 343, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=11, question_id='353ced19c93a7d36a0280d1e92420f2f', canonical_span=NumericRange(172, 179, '[)'), mention_type='ORG', gloss='Gannett Co.', weight=1.0, tm_gloss='Gannett Co.', sm_span=NumericRange(332, 343, '[)'), sm_gloss='Gannett Co.', sm_canonical_span=NumericRange(172, 179, '[)')), 'Correct'], 
            [Record(assignment_id='3DYGAII7PM2Z9Z6QFQTI9JABSBCQP6', doc_id='NYT_ENG_20130702.0065', span=NumericRange(3809, 3823, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=11, question_id='dc0fb15b56460d629fbcf32f2b608990', canonical_span=NumericRange(3809, 3823, '[)'), mention_type='ORG', gloss='New York Times', weight=1.0, tm_gloss='New York Times', sm_span=NumericRange(3809, 3823, '[)'), sm_gloss='New York Times', sm_canonical_span=NumericRange(3809, 3823, '[)')), 'Correct'], 
            [Record(assignment_id='3AUQQEL7U6NOQQYNK482058B1WK0VA', doc_id='NYT_ENG_20130730.0076', span=NumericRange(3474, 3488, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=10, question_id='52bead947891c50f518d44cd05df8361', canonical_span=NumericRange(3474, 3488, '[)'), mention_type='PER', gloss='Naomi Mitchell', weight=1.0, tm_gloss='Naomi Mitchell', sm_span=NumericRange(3474, 3488, '[)'), sm_gloss='Naomi Mitchell', sm_canonical_span=NumericRange(3474, 3488, '[)')), 'Correct'], 
            [Record(assignment_id='3QBD8R3Z22DAZU7R2T9QHG4GMES4OF', doc_id='ENG_NW_001278_20130822_F00012Q53', span=NumericRange(257, 263, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=3, question_id='b8473bb8b1210e693debef7a515af441', canonical_span=NumericRange(152, 158, '[)'), mention_type='GPE', gloss='Israel', weight=1.0, tm_gloss='Israel', sm_span=NumericRange(257, 263, '[)'), sm_gloss='Israel', sm_canonical_span=NumericRange(257, 263, '[)')), 'Correct'], 
            [Record(assignment_id='34Q075JO1Y784EIPDQODTH1VB7F10H', doc_id='ENG_NW_001436_20150718_F0010006Q', span=NumericRange(1431, 1434, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=2, question_id='0078e08b36a219f5e092f2455149b768', canonical_span=NumericRange(313, 316, '[)'), mention_type='ORG', gloss='NSA', weight=1.0, tm_gloss=None, sm_span=None, sm_gloss=None, sm_canonical_span=None), 'Delete'], 
            [Record(assignment_id='3OE22WJIGJIC14EMWCSCJPXAZ8AQU3', doc_id='ENG_NW_001432_20150622_F0010006L', span=NumericRange(3214, 3224, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=2, question_id='5f49bf3cb38d1f2c0c06014e47e8fb8d', canonical_span=NumericRange(931, 941, '[)'), mention_type='PER', gloss='Paige Roof', weight=1.0, tm_gloss=None, sm_span=None, sm_gloss=None, sm_canonical_span=None), 'Delete'], 
            [Record(assignment_id='3BC8WZX3V4QKXD155XM7J4KVOU0RRR', doc_id='ENG_NW_001435_20150718_F0010006O', span=NumericRange(743, 749, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=2, question_id='7b8a751495c6c549f6d9c51a274f1464', canonical_span=NumericRange(743, 749, '[)'), mention_type='DATE', gloss='friday', weight=1.0, tm_gloss=None, sm_span=None, sm_gloss=None, sm_canonical_span=None), 'Delete'], 
            [Record(assignment_id='3WMINLGALCXOSUQ5LPAQZJWZOPBACY', doc_id='ENG_NW_001435_20150718_F0010006O', span=NumericRange(2335, 2337, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=2, question_id='7b8a751495c6c549f6d9c51a274f1464', canonical_span=NumericRange(1154, 1164, '[)'), mention_type='PER', gloss='He', weight=1.0, tm_gloss=None, sm_span=None, sm_gloss=None, sm_canonical_span=None), 'Delete'], 
            [Record(assignment_id='3WMINLGALCXOSUQ5LPAQZJWZOPBACY', doc_id='ENG_NW_001435_20150718_F0010006O', span=NumericRange(1119, 1147, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=2, question_id='7b8a751495c6c549f6d9c51a274f1464', canonical_span=NumericRange(1119, 1147, '[)'), mention_type='ORG', gloss='Army Public Relations (DAPR)', weight=1.0, tm_gloss=None, sm_span=None, sm_gloss=None, sm_canonical_span=None), 'Delete'], 
            [Record(assignment_id='3GU1KF0O4JVC5T41W8WSEUFC6CHBPN', doc_id='NYT_ENG_20130720.0038', span=NumericRange(878, 917, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=12, question_id='a2e0a0b7cd1315b62bd9492e3144ce15', canonical_span=NumericRange(878, 917, '[)'), mention_type='ORG', gloss="America's First Female Rocket Scientist", weight=1.0, tm_gloss='America’s First Female Rocket Scientist', sm_span=NumericRange(878, 917, '[)'), sm_gloss="America's First Female Rocket Scientist", sm_canonical_span=NumericRange(878, 917, '[)')), 'Replace gloss'], 
            [Record(assignment_id='3X3OR7WPZ0U3CARW14JB6BGRTWVL80', doc_id='NYT_ENG_20130617.0145', span=NumericRange(1510, 1535, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=10, question_id='d6f1d10aa7cf717eef1b228f3a248bf0', canonical_span=NumericRange(1510, 1535, '[)'), mention_type='ORG', gloss='Slate, Meagher & Flom', weight=1.0, tm_gloss='Slate, Meagher &amp; Flom', sm_span=NumericRange(1510, 1535, '[)'), sm_gloss='Slate, Meagher & Flom', sm_canonical_span=NumericRange(1510, 1535, '[)')), 'Replace gloss'], 
            [Record(assignment_id='30BUDKLTXEP6JMY2MKP4HWGGI91E5C', doc_id='NYT_ENG_20131108.0248', span=NumericRange(2933, 2973, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=3, question_id='019a6c70573d42c553a7a05fd0608399', canonical_span=NumericRange(2933, 2973, '[)'), mention_type='ORG', gloss="U.S. Navy's Joint Typhoon Warning Center", weight=1.0, tm_gloss='U.S. Navy’s Joint Typhoon Warning Center', sm_span=NumericRange(2933, 2942, '[)'), sm_gloss='U.S. Navy', sm_canonical_span=NumericRange(2933, 2942, '[)')), 'Replace gloss'], 
            [Record(assignment_id='33NF62TLXKWHCL5X7841G1CQK7JJKE', doc_id='NYT_ENG_20130617.0145', span=NumericRange(1510, 1535, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=10, question_id='a42c3df8b30447d24dc37de9a0a9c70c', canonical_span=NumericRange(1510, 1535, '[)'), mention_type='ORG', gloss='Slate, Meagher & Flom', weight=1.0, tm_gloss='Slate, Meagher &amp; Flom', sm_span=NumericRange(1510, 1535, '[)'), sm_gloss='Slate, Meagher & Flom', sm_canonical_span=NumericRange(1510, 1535, '[)')), 'Replace gloss'], 
            [Record(assignment_id='33SA9F9TRYO0W5DMILCD7WTT25OWES', doc_id='ENG_NW_001278_20130514_F000139UN', span=NumericRange(655, 662, '[)'), created=datetime.datetime(2017, 4, 14, 13, 30, 40, 862161), question_batch_id=3, question_id='809ed3d2d07fbac544ffb46740956bdc', canonical_span=NumericRange(655, 662, '[)'), mention_type='ORG', gloss='P&G', weight=1.0, tm_gloss='P&amp;G', sm_span=NumericRange(655, 662, '[)'), sm_gloss='P&G', sm_canonical_span=NumericRange(655, 662, '[)')), 'Replace gloss']
            ]
    for test_case in test_cases:
        assert sanitize_mention_response(test_case[0]) == test_case[1]

def sanitize_mention_response_table():
    """Make sure mention responses are correct and correct them if possible"""
    db.execute(
    """
    CREATE OR REPLACE VIEW mention_gloss_true AS 
        (SELECT m.doc_id, m.span, substring(s.gloss from lower(m.span)-lower(s.span)+1 for upper(m.span)-lower(m.span)) as gloss 
            FROM (SELECT distinct doc_id, span  FROM evaluation_mention_response) as m 
        LEFT JOIN sentence AS s ON m.doc_id = s.doc_id AND m.span <@ s.span);
    """);
    def clean_whitespaces():
        print(db.CONN.cursor().mogrify(r"""UPDATE evaluation_mention_response SET gloss = replace(gloss, E'\302\240', ' ')"""))
        db.execute(r"""UPDATE evaluation_mention_response SET gloss = replace(gloss, E'\302\240', ' ')""")

    clean_whitespaces()
    responses_with_true_gloss = db.select("""
            SELECT m.*, tm.gloss AS tm_gloss, sm.span as sm_span, sm.gloss as sm_gloss, sm.canonical_span as sm_canonical_span
            FROM evaluation_mention_response AS m 
            LEFT JOIN mention_gloss_true AS tm ON m.doc_id = tm.doc_id AND m.span = tm.span 
            LEFT JOIN suggested_mention AS sm on sm.doc_id = m.doc_id AND sm.span && m.span AND sm.mention_type = m.mention_type 
            ORDER BY upper(sm.span*m.span) - lower(sm.span*m.span);""");
    changes_counter = Counter()
    for response in tqdm(responses_with_true_gloss): 
        action = sanitize_mention_response(response)
        changes_counter[action]+=1
        if action == 'Correct':
            continue
        elif action == 'Delete':
            with db.CONN: 
                with db.CONN.cursor() as cur:
                    db.execute("""DELETE FROM evaluation_mention_response
                    WHERE assignment_id = %(assignment_id)s AND doc_id = %(doc_id)s AND span = %(span)s""", 
                    cur = cur, 
                    assignment_id = response.assignment_id, 
                    doc_id = response.doc_id, 
                    span = response.span)
                    db.execute("""DELETE FROM evaluation_mention_response
                    WHERE assignment_id = %(assignment_id)s AND doc_id = %(doc_id)s AND canonical_span = %(span)s""", 
                    cur = cur, 
                    assignment_id = response.assignment_id, 
                    doc_id = response.doc_id, 
                    span = response.span)


        elif action == 'Replace gloss':
            db.execute("""UPDATE evaluation_mention_response
            SET gloss = %(new_gloss)s
            WHERE assignment_id = %(assignment_id)s AND doc_id = %(doc_id)s AND span = %(span)s""", 
            assignment_id = response.assignment_id, 
            doc_id = response.doc_id, 
            span = response.span, 
            new_gloss = response.tm_gloss
            )

        elif action == 'Replace with suggested':
            with db.CONN: 
                with db.CONN.cursor() as cur:
                    db.execute("""UPDATE evaluation_mention_response
                    SET span = %(new_span)s, gloss = %(new_gloss)s, canonical_span = %(new_canonical_span)s
                    WHERE assignment_id = %(assignment_id)s AND doc_id = %(doc_id)s AND span = %(span)s""", 
                    cur = cur, 
                    assignment_id = response.assignment_id, 
                    doc_id = response.doc_id, 
                    span = response.span, 
                    new_span = response.sm_span, 
                    new_gloss = response.sm_gloss,
                    new_canonical_span = response.sm_canonical_span
                    )
                    db.execute("""UPDATE evaluation_mention_response
                    SET canonical_span = %(new_span)s
                    WHERE assignment_id = %(assignment_id)s AND doc_id = %(doc_id)s AND canonical_span = %(span)s""", 
                    cur = cur, 
                    assignment_id = response.assignment_id, 
                    doc_id = response.doc_id, 
                    span = response.span,
                    new_span = response.sm_span
                    )
        else:
            assert False, "Undefined action:"+ action
        
    print(changes_counter)
    
    #Test case generation
    #test_examples = defaultdict(list)
    #for response in responses_with_true_gloss: 
        #test_examples[sanitize_mention_response(response)].append(response)

    #for k, vs in test_examples.items():
    #    for rand_idx in np.random.randint(len(vs), size = 5): 
    #        print([vs[rand_idx], k])

if __name__ == '__main__':
    #sanitize_mention_response_table()
    #merge_evaluation_table('mention', mode='all')
    parse_responses()
    merge_evaluation_table('link', mode='all')
    #test_sanitize_mention_response()
        




    

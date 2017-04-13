#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities to handle conversion and interaction of data in JSON
"""
import json
import logging
from collections import Counter

from . import db
from .schema import Provenance, MentionInstance, LinkInstance, RelationInstance, EvaluationMentionResponse, EvaluationLinkResponse, EvaluationRelationResponse

logger = logging.getLogger(__name__)

def parse_selective_relations_response(question, responses):
    mentions, links, relations = [], [], []
    for response in responses:
        doc_id = question["doc_id"]
        subject_id = Provenance(doc_id, response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])
        subject_canonical_id = Provenance(doc_id, response["subject"]["entity"]["doc_char_begin"], response["subject"]["entity"]["doc_char_end"])
        subject_type = response["subject"]["type"]["name"].strip()
        subject_gloss = response["subject"]["gloss"].strip()

        object_id = Provenance(doc_id, response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        object_canonical_id = Provenance(doc_id, response["object"]["entity"]["doc_char_begin"], response["object"]["entity"]["doc_char_end"])
        object_type = response["object"]["type"]["name"].strip()
        object_gloss = response["object"]["gloss"].strip()

        assert "canonicalCorrect" in response["subject"]["entity"]
        if "canonicalCorrect" in response["subject"]["entity"]:
            mentions.append(MentionInstance(subject_id, subject_canonical_id, subject_type, subject_gloss, 1.0 if response["subject"]["entity"]["canonicalCorrect"] == "Yes" else 0.0))
        if "canonicalCorrect" in response["object"]["entity"]:
            mentions.append(MentionInstance(object_id, object_canonical_id, object_type, object_gloss, 1.0 if response["object"]["entity"]["canonicalCorrect"] == "Yes" else 0.0))
        if "linkCorrect" in response["subject"]["entity"]:
            links.append(LinkInstance(subject_id, response["subject"]["entity"]["link"], 1.0 if response["subject"]["entity"]["linkCorrect"] == "Yes" else 0.0))
        if "linkCorrect" in response["object"]["entity"]:
            links.append(LinkInstance(object_id, response["object"]["entity"]["link"], 1.0 if response["object"]["entity"]["linkCorrect"] == "Yes" else 0.0))

        relations.append(RelationInstance(subject_id, object_id, response["relation"], 1.0))
    return sorted(set(mentions)), sorted(set(links)), sorted(set(relations))

def test_parse_selective_relations_response():
    # My output could be one of the following cases:
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
        subject = Provenance(doc_id, response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])
        object_ = Provenance(doc_id, response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        relation = RelationInstance(subject, object_, response["relation"], 1.0)
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
            id_ = Provenance(doc_id, entity["doc_char_begin"], entity["doc_char_end"])
            type_ = entity["type"]["name"].strip()
            gloss = entity["gloss"].strip()

            canonical_id = Provenance(doc_id, entity["entity"]["doc_char_begin"], entity["entity"]["doc_char_end"])
            mention = MentionInstance(id_, canonical_id, type_, gloss, 1.0)
            mentions.append(mention)

            if id_ == canonical_id:
                link = LinkInstance(id_, entity["entity"]["link"], 1.0)
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

    for row in db.pg_select("""
SELECT a.id AS assignment_id, b.id AS question_batch_id, q.id AS question_id, b.batch_type, q.params AS question, a.response AS response
FROM mturk_assignment a,
     mturk_hit h,
     evaluation_question q,
     evaluation_batch b
WHERE a.hit_id = h.id AND h.question_id = q.id AND h.question_batch_id = q.batch_id AND b.id = q.batch_id
 AND NOT a.ignored"""): # Q: Should there be a fixed type?
        if len(row.response) == 0:
            logger.warning("Empty response : %s", row)
            continue

        question = json.loads(row.question)
        response = json.loads(row.response)

        if row.batch_type == "selective_relations":
            mentions, links, relations = parse_selective_relations_response(question, response)
        elif row.batch_type == "exhaustive_relations":
            mentions, links, relations = parse_exhaustive_relations_response(question, response)
        elif row.batch_type == "exhaustive_entities":
            mentions, links, relations = parse_exhaustive_entities_response(question, response)
        else:
            raise ValueError("Unexpected batch type: " + row.batch_type)

        raise Exception()

        # evaluation_mention_response
        for mention in mentions:
            response = EvaluationMentionResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                mention.id.doc_id,
                mention.id,
                mention.canonical_id,
                mention.type,
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
                link.id.doc_id,
                link.id,
                link.link_name,
                link.weight,))

        for relation in relations:
            evaluation_relations.append(EvaluationRelationResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                relation.subject_id.doc_id,
                relation.subject_id,
                relation.object_id,
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
            db.execute_values(cur, """INSERT INTO evaluation_mention_response(assignment_id, question_batch_id, question_id, doc_id, mention_id, canonical_id, mention_type, gloss, weight) VALUES %s""", evaluation_mentions)
            db.execute_values(cur, """INSERT INTO evaluation_link_response(assignment_id, question_batch_id, question_id, doc_id, mention_id, link_name, weight) VALUES %s""", evaluation_links)
            db.execute_values(cur, """INSERT INTO evaluation_relation_response(assignment_id, question_batch_id, question_id, doc_id, subject_id, object_id, relation, weight) VALUES %s""", evaluation_relations)

def majority_element(lst):
    return Counter(lst).most_common(1)[0][0]

def merge_evaluation_mentions(row):
    # Choose the most frequent char_begin and char_end.
    #TODO: the elements in lst should be weighed by the weight of their vote (e.g. canonical_mention if wrong)
    canonical_begin, canonical_end = majority_element((b,e) for b,e,w in zip(row.canonical_char_begins, row.canonical_char_ends, row.weights) if w > 0.5)
    mention_type = majority_element(row.mention_types)
    gloss = majority_element(row.glosses)
    weight = sum(weight for weight, canonical_begin_, canonical_end_ in zip(row.weights, row.canonical_char_begins, row.canonical_char_ends) if canonical_begin_ == canonical_begin and canonical_end_ == canonical_end)/len(row.weights)

    return row.doc_id, row.mention_id, (row.doc_id, canonical_begin, canonical_end), mention_type, gloss, weight

def merge_evaluation_links(row):
    link_name = majority_element(row.link_names)
    weight = sum(weight for weight, link_name_ in zip(row.weights, row.link_names) if link_name_ == link_name)/len(row.weights)

    return row.doc_id, row.mention_id, link_name, weight

def merge_evaluation_relations(row):
    # Choose the most frequent char_begin and char_end.
    relation = majority_element(row.relations)
    n_assignments = max(max([int(json.loads(params)['max_assignments']) for params in row.params]), len(row.weights))

    param = majority_element(row.params)
    weight = sum(weight for weight, relation_ in zip(row.weights, row.relations) if relation_ == relation)/n_assignments

    return row.question_id, row.question_batch_id, row.doc_id, row.subject_id, row.object_id, relation, weight

def update_evaluation_mention():
    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""TRUNCATE evaluation_mention;""")
            # For evaluation_mention, we want to aggregate both types and canonical_ids.
            cur.execute("""SELECT doc_id, mention_id, 
                    array_agg((canonical_id).char_begin) AS canonical_char_begins, array_agg((canonical_id).char_end) AS canonical_char_ends,
                    array_agg(mention_type) AS mention_types, array_agg(gloss) AS glosses,
                    array_agg(weight) as weights FROM evaluation_mention_response GROUP BY doc_id, mention_id""")
            # Take the majority vote on this mention iff count > 1.
            values = [merge_evaluation_mentions(row) for row in cur]
            db.execute_values(cur, """INSERT INTO evaluation_mention(doc_id, mention_id, canonical_id, mention_type, gloss, weight) VALUES %s""", values)

def update_evaluation_link():
    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""TRUNCATE evaluation_link;""")
            # For evaluation_mention, we want to aggregate both types and canonical_ids.
            cur.execute("""SELECT doc_id, mention_id, array_agg(link_name) AS link_names, array_agg(weight) AS weights FROM evaluation_link_response GROUP BY doc_id, mention_id""")
            # Take the majority vote on this mention iff count > 1.
            values = [merge_evaluation_links(row) for row in cur]
            db.execute_values(cur, """INSERT INTO evaluation_link(doc_id, mention_id, link_name, weight) VALUES %s""", values)

def update_evaluation_relation():
    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""TRUNCATE evaluation_relation;""")
            # For evaluation_mention, we want to aggregate both types and canonical_ids.
            cur.execute("""SELECT question_id, question_batch_id, doc_id, subject_id, object_id, array_agg(relation) AS relations, array_agg(weight) as weights, array_agg(params) as params FROM evaluation_relation_response as r, mturk_assignment as a, mturk_batch as b WHERE r.assignment_id = a.id AND a.batch_id = b.id GROUP BY question_id, question_batch_id, doc_id, subject_id, object_id""")
            # Take the majority vote on this mention iff count > 1.
            values = [merge_evaluation_relations(row) for row in cur]
            db.execute_values(cur, """INSERT INTO evaluation_relation(question_id, question_batch_id, doc_id, subject_id, object_id, relation, weight) VALUES %s""", values)

def update_summary():
    """
    Updates the evaluation_mention, evaluation_link and evaluation_relation tables.
    """
    update_evaluation_mention()
    update_evaluation_link()
    update_evaluation_relation()

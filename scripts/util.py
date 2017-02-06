#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for querying the database
"""

import os
import re
import random
import shlex
import subprocess
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ner_map = {
    "PERSON": "PER",
    "ORGANIZATION": "ORG",
    "COUNTRY": "GPE",
    "LOCATION": "GPE",
    "CITY": "GPE",
    "STATE_OR_PROVINCE": "GPE",
    "GPE": "GPE",
    "TITLE": "TITLE",
    "DATE": "DATE",
    }
TYPES = list(ner_map.values())

RELATION_MAP = {
    "per:alternate_names":"per:alternate_names",

    "per:place_of_birth":"per:place_of_birth",
    "per:city_of_birth":"per:place_of_birth",
    "per:stateorprovince_of_birth":"per:place_of_birth",
    "per:country_of_birth":"per:place_of_birth",

    "per:place_of_residence":"per:place_of_residence",
    "per:cities_of_residence":"per:place_of_residence",
    "per:stateorprovinces_of_residence":"per:place_of_residence",
    "per:countries_of_residence":"per:place_of_residence",

    "per:place_of_death":"per:place_of_death",
    "per:city_of_death":"per:place_of_death",
    "per:stateorprovince_of_death":"per:place_of_death",
    "per:country_of_death":"per:place_of_death",

    "per:date_of_birth":"per:date_of_birth",
    "per:date_of_death":"per:date_of_death",
    "per:organizations_founded":"per:organizations_founded",
    "per:holds_shares_in":"per:holds_shares_in",
    "per:schools_attended":"per:schools_attended",
    "per:employee_or_member_of":"per:employee_or_member_of",
    "per:parents":"per:parents",
    "per:children":"per:children",
    "per:spouse":"per:spouse",
    "per:sibling":"per:sibling",
    "per:other_family":"per:other_family",
    "per:title":"per:title",

    "org:alternate_names":"org:alternate_names",

    "org:place_of_headquarters":"org:place_of_headquarters",
    "org:city_of_headquarters":"org:place_of_headquarters",
    "org:stateorprovince_of_headquarters":"org:place_of_headquarters",
    "org:country_of_headquarters":"org:place_of_headquarters",

    "org:date_founded":"org:date_founded",
    "org:date_dissolved":"org:date_dissolved",
    "org:founded_by":"org:founded_by",
    "org:member_of":"org:member_of",
    "org:members":"org:members",
    "org:subsidiaries":"org:subsidiaries",
    "org:parents":"org:parents",
    "org:shareholders":"org:shareholders",
    "org:holds_shares_in":"org:holds_shares_in",

    "gpe:births_in_place":"gpe:births_in_place",
    "gpe:births_in_city":"gpe:births_in_place",
    "gpe:births_in_stateorprovince":"gpe:births_in_place",
    "gpe:births_in_country":"gpe:births_in_place",

    "gpe:residents_in_place": "gpe:residents_in_place",
    "gpe:residents_in_city": "gpe:residents_in_place",
    "gpe:residents_in_stateorprovince": "gpe:residents_in_place",
    "gpe:residents_in_country": "gpe:residents_in_place",

    "gpe:deaths_in_place": "gpe:deaths_in_place",
    "gpe:deaths_in_city": "gpe:deaths_in_place",
    "gpe:deaths_in_stateorprovince": "gpe:deaths_in_place",
    "gpe:deaths_in_country": "gpe:deaths_in_place",

    "gpe:employees_or_members": "gpe:employees_or_members",
    "gpe:holds_shares_in": "gpe:holds_shares_in",
    "gpe:organizations_founded": "gpe:organizations_founded",
    "gpe:member_of": "gpe:member_of",

    "gpe:headquarters_in_place":"gpe:headquarters_in_place",
    "gpe:headquarters_in_city":"gpe:headquarters_in_place",
    "gpe:headquarters_in_stateorprovince":"gpe:headquarters_in_place",
    "gpe:headquarters_in_country":"gpe:headquarters_in_place",

    "no_relation":"no_relation",
    }
ALL_RELATIONS = list(RELATION_MAP.values())
RELATIONS = [
    "per:alternate_names",
    "per:place_of_birth",
    "per:place_of_residence",
    "per:place_of_death",
    "per:date_of_birth",
    "per:date_of_death",
    "per:organizations_founded",
    "per:holds_shares_in",
    "per:schools_attended",
    "per:employee_or_member_of",
    "per:parents",
    "per:children",
    "per:spouse",
    "per:sibling",
    "per:other_family",
    "per:title",
    "org:alternate_names",
    "org:place_of_headquarters",
    "org:date_founded",
    "org:date_dissolved",
    "org:founded_by",
    "org:member_of",
    "org:members",
    "org:subsidiaries",
    "org:parents",
    "org:shareholders",
    "org:holds_shares_in",
    "no_relation",
    ]

INVERTED_RELATIONS = {
    "per:children":["per:parents"],
    "per:other_family":["per:other_family"],
    "per:parents":["per:children"],
    "per:sibling":["per:sibling"],
    "per:spouse":["per:spouse"],
    "per:employee_or_member_of":["org:employees_or_members","gpe:employees_or_members"],
    "per:schools_attended":["org:students"],
    "per:place_of_birth":["gpe:births_in_place"],
    "per:place_of_residence":["gpe:residents_in_place"],
    "per:place_of_death":["gpe:deaths_in_place"],
    "per:organizations_founded":["org:founded_by"],
    "per:holds_shares_in":["org:shareholders"],

    "org:shareholders":["per:holds_shares_in","org:holds_shares_in","gpe:holds_shares_in"],
    "org:holds_shares_in":["org:shareholders"],
    "org:founded_by":["per:organizations_founded","org:organizations_founded","gpe:organizations_founded"],
    "org:organizations_founded":["org:founded_by",],
    "org:employees_or_members": ["per:employee_or_member_of"],
    "org:member_of":["org:members"],
    "org:members":["gpe:member_of","org:member_of"],
    "org:students":["per:schools_attended"],
    "org:subsidiaries":["org:parents"],
    "org:parents":["org:subsidiaries"],
    "org:place_of_headquarters":["gpe:headquarters_in_place"],

    "gpe:births_in_place":["per:place_of_birth"],
    "gpe:residents_in_place":["per:place_of_residence"],
    "gpe:deaths_in_place":["per:place_of_death"],
    "gpe:employees_or_members": ["per:employee_or_member_of"],
    "gpe:holds_shares_in":["org:shareholders"],
    "gpe:organizations_founded":["org:founded_by",],
    "gpe:member_of":["org:members"],
    "gpe:headquarters_in_place":["org:place_of_headquarters"],
    }

def unescape_sql(inp):
    if inp.startswith('"') and inp.endswith('"'):
        inp = inp[1:-1]
    return inp.replace('""','"').replace('\\\\','\\')

def parse_psql_array(inp):
    """
    Parses a postgres array.
    """
    inp = unescape_sql(inp)
    # Strip '{' and '}'
    if inp.startswith("{") and inp.endswith("}"):
        inp = inp[1:-1]

    lst = []
    elem = ""
    in_quotes, escaped = False, False

    for ch in inp:
        if escaped:
            elem += ch
            escaped = False
        elif ch == '"':
            in_quotes = not in_quotes
            escaped = False
        elif ch == '\\':
            escaped = True
        else:
            if in_quotes:
                elem += ch
            elif ch == ',':
                lst.append(elem)
                elem = ""
            else:
                elem += ch
            escaped = False
    if len(elem) > 0:
        lst.append(elem)
    return lst

def test_parse_psql_array():
    inp = '{Bond,was,set,at,$,"1,500",each,.}'
    lst = ["Bond", "was", "set", "at", "$", "1,500", "each","."]
    lst_ = parse_psql_array(inp)
    assert all([x == y for (x,y) in zip(lst, lst_)])

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def sample(lst, n):
    """
    Sample @n elements from @lst randomly.
    """
    return sorted(lst, key=lambda *args: random.random())[:n]

def sanitize(word):
    """
    Remove any things that would confusing psql.
    """
    return re.sub(r"[^a-zA-Z0-9 ]", "%", word)

def make_list(lst):
    """
    Pretty format a list of strings for psql
    """
    return ",".join("'{}'".format(d) for d in lst)

def make_nlist(lst):
    """
    Pretty format a list of numbers for psql
    """
    return ",".join("{}".format(d) for d in lst)

def parse_input(stream):
    """
    Reorder input to always have mention defintions first, followed by
    links, canonical mentions and relations.
    """
    mentions = []
    links = []
    canonical_mentions = []
    relations = []

    for row in stream:
        relation = row[1]
        if relation in TYPES:
            mentions.append(row)
        elif relation == "link":
            links.append(row)
        elif relation == "canonical_mention":
            canonical_mentions.append(row)
        else:
            relations.append(row)

    return mentions, links, canonical_mentions, relations



def query_psql(sql):
    """
    Sends a query to psql.
    """
    #logger.debug("Querying %s", sql)

    cmd = r"""psql -h localhost -p 4242 kbp kbp"""
    sql_cmd = "COPY ({sql}) TO STDOUT DELIMITER E'\t'".format(sql=sql)
    output = subprocess.run(shlex.split(cmd), input=sql_cmd, stdout=subprocess.PIPE, universal_newlines=True, check=True).stdout

    for line in output.split("\n"):
        if len(line) == 0: continue
        yield tuple(line.split("\t"))

def query_docs(corpus_id, keywords=None, sentence_table="sentence"):
    """
    List all documents from @corpus_id which match the given @keywords.
    """
    if keywords is None:
        keywords = []

    qry = """
SELECT DISTINCT(doc_id) 
FROM {sentence}
WHERE corpus_id = {corpus_id} {addtl} 
  AND doc_id IN (SELECT doc_id FROM document_date)
ORDER BY doc_id"""

    addtl = " AND ".join("gloss ILIKE '%{word}%'".format(word=sanitize(word)) for word in keywords)
    if addtl:
        addtl = " AND " + addtl
    return query_psql(qry.format(corpus_id=corpus_id, sentence=sentence_table, addtl=addtl))

def query_wikilinks(fb_ids):
    qry = "SELECT fb_id, wiki_id FROM fb_to_wiki_map WHERE fb_id IN ({fb_ids})"
    return query_psql(qry.format(fb_ids=make_list(fb_ids)))

def query_entities(doc_ids, mention_table="mention"):
    """
    Get all (canonical) entities across these @doc_ids.
    """
    qry = """
SELECT max(gloss), COUNT(*)
FROM {mention}
WHERE doc_canonical_char_begin = doc_char_begin AND doc_canonical_char_end = doc_char_end 
AND ner IN ('PERSON', 'ORGANIZATION', 'GPE') 
AND doc_id IN ({doc_ids})
GROUP BY best_entity"""
    return query_psql(qry.format(doc_ids=make_list(doc_ids), mention=mention_table))

def query_dates(doc_ids):
    """
    Get all dates for these @doc_ids.
    """
    qry = """
SELECT doc_id, date
FROM document_date 
WHERE doc_id IN ({doc_ids})"""
    return query_psql(qry.format(doc_ids=",".join("'{}'".format(d) for d in doc_ids)))

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

    for row in query_psql(qry.format(docid, sentence=sentence_table)):
        _, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = row

        # Happens in some DF
        #assert int(idx) == idx_, "Seems to have skipped a line: {} != {}".format(idx, idx_)
        words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = map(parse_psql_array, (words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end))
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
    for row in query_psql(qry.format(doc_id=docid, mention=mention_table)):
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
WHERE m.id IN ({mention_ids})
  AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
  AND m.parent_id IS NULL
  AND n.parent_id IS NULL
ORDER BY doc_id, doc_char_begin, doc_char_end
"""
    return query_psql(qry.format(mention=mention_table, mention_ids=make_list(mention_ids)))

def query_mention_ids(mention_ids, mention_table="mention"):
    qry = """
SELECT m.id
  FROM {mention} m, {mention} n
 WHERE m.id IN ({mention_ids})
   AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
   AND m.parent_id IS NULL
   AND n.parent_id IS NULL
UNION
SELECT n.id
  FROM {mention} m, {mention} n
 WHERE m.id IN ({mention_ids})
   AND m.doc_id = n.doc_id AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
   AND m.parent_id IS NULL
   AND n.parent_id IS NULL
"""
    return set(m for m, in query_psql(qry.format(mention=mention_table, mention_ids=make_list(mention_ids))))

def normalize(types, entry):
    subj, reln, obj = entry[0], entry[1], entry[2]
    if reln in RELATIONS:
        return entry
    elif reln not in RELATIONS and reln in INVERTED_RELATIONS:
        for reln_ in INVERTED_RELATIONS[reln]:
            if reln_.startswith(types[obj].lower()):
                entry = [obj, reln_, subj] + list(entry[3:])
                return tuple(entry)
    else:
        logger.fatal("Couldn't map relation for %s", entry)

def map_relations(mentions, relations):
    types = {r[0]: r[1] for r in mentions}
    for entry in relations:
        yield normalize(types, entry)

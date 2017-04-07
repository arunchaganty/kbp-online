#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Score data

Output format:
mention_id type gloss provenance _
mention_id canonical_mention mention_id_ _ confidence
mention_id link entity_id _ confidence
mention_id relation mention_id_ provenance confidence
"""

import os
import csv
import random
import json
import sys
import logging
from collections import defaultdict, Counter, namedtuple

from util import normalize, map_relations, make_list, query_psql, query_doc, query_mention_ids, query_mentions_by_id, ensure_dir, sample, ner_map, TYPES, ALL_RELATIONS, RELATIONS, INVERTED_RELATIONS, parse_input

KnowledgeBase = namedtuple('KnowledgeBase', ['mentions', 'links', 'canonical_mentions', 'relations'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def is_reln(reln):
    return reln not in TYPES and reln != "canonical_mention" and reln != "link"

def as_prov(doc_id, begin, end):
    return "{}:{}-{}".format(doc_id, begin, end)

def parse_prov(prov):
    doc_id, begin_end = prov.split(":")
    begin, end = begin_end.split("-")
    return doc_id, int(begin), int(end)

def sample_by_relation(types, entries, num_entries, old_entries):
    # Construct an entity-centric table to sample from.
    links = {}
    entities = defaultdict(lambda: defaultdict(list))
    relations = defaultdict(list)

    old_entries = set()
    for r in old_entries:
        old_entries.add((r[0], r[2]))
        if r[1] in INVERTED_RELATIONS:
            old_entries.add((r[2], r[0]))

    # Summary statistics
    for row in entries:
        subj, relation, obj, _, _ = row
        if relation in TYPES:
            continue
        if relation == "link":
            links[subj] = obj
        elif relation == "canonical_mention":
            links[subj] = links[obj]
        else:
            if (row[0], row[2]) in old_entries: continue # skip old_entries
            subj_, obj_ = links[subj], links[obj]

            row = normalize(types, row) # Normalize every entry before adding it here.
            relation = row[1]
            entities[subj_][(relation,obj_)].append(tuple(row))
            relations[relation].append(tuple(row))

    E, F, I = len(entities), sum(len(fills) for fills in entities.values()), sum(len(instances) for fills in entities.values() for instances in fills.values())
    I_ = sum(len(mentions) for mentions in relations.values())
    assert I == I_, "Discrepancy in relation, entity counts."

    logger.info("Found at %d entities, %d fills, %d instances split over %d relations", E, F, I, len(relations))

    new_entries = {}

    remaining_entries = num_entries
    # Sort relations by decreasing frequency.
    for i, (relation, instances) in enumerate(sorted(sorted(relations.items()), key=lambda t:len(t[1]))):
        remaining_relations = len(relations) - i
        per_relation = int(remaining_entries / remaining_relations)

        instances = [instance for instance in instances if (instance[0], instance[2]) not in new_entries]
        random.shuffle(instances)
        for instance in instances[:per_relation]:
            subj_, reln, obj_ = links[instance[0]], instance[1], links[instance[2]]
            # Inverted probabilities
            p_mi = I
            p_ei = E * len(entities[subj_]) * len(entities[subj_][reln,obj_]) # fills_e, instances_e
            p_ri = len(instances) * num_entries / min(len(instances), per_relation) # This latter should be len(relations) if there were enough.
            p_rt = len(instances) * len(relations) # True distribution / desired distribution.
            # Weights
            mention_weight = p_ri/p_mi
            entity_weight = p_ri/p_ei
            relation_weight = p_ri/p_rt

            new_entries[(instance[0], instance[2])] = instance + (mention_weight, entity_weight, relation_weight)
            remaining_entries -= 1 # a new entry was added!

        logger.info("Currently at %d relations with %s", len(new_entries), relation)
    logger.info("Done with %d relations", len(new_entries))

    return sorted(new_entries.values())

def sample_by_entity(types, entries, num_entries, per_entity, old_entries):
    # Construct an entity-centric table to sample from.
    links = {}
    entities = defaultdict(lambda: defaultdict(list))

    old_entries = set()
    for r in old_entries:
        old_entries.add((r[0], r[2]))
        if r[1] in INVERTED_RELATIONS:
            old_entries.add((r[2], r[0]))

    # Summary statistics
    for row in entries:
        subj, relation, obj, _, _ = row
        if relation in TYPES:
            continue
        if relation == "link":
            links[subj] = obj
        elif relation == "canonical_mention":
            links[subj] = links[obj]
        else:
            if (row[0], row[2]) in old_entries: continue # skip old_entries
            subj_, obj_ = links[subj], links[obj]
            row = normalize(types, row)

            entities[subj_][(relation,obj_)].append(tuple(row)) # Normalize every entry before adding it here.
    E, F, I = len(entities), sum(len(fills) for fills in entities.values()), sum(len(instances) for fills in entities.values() for instances in fills.values())

    # Relation counts reflect normalized values.
    R = Counter(instance[1] for fills in entities.values() for instances in fills.values() for instance in instances)

    logger.info("Found at %d entities, %d fills and %d instances", E, F, I)
    logger.info("Relations: %s", R)

    new_entries = {}
    condition = lambda: len(new_entries) < num_entries

    entities_ = sorted(sorted(entities.keys()), key=lambda *args: random.random())
    for entity in entities_:
        fills = entities[entity]

        # TODO: Actually sample without replacement rather than this
        # weird funky rejection sampling shit.

        # sample a couple of fills yo.
        for _ in range(per_entity):
            fill = random.choice(list(fills.keys()))
            instances = fills[fill]
            instance = random.choice(instances)
            if (instance[0], instance[2]) in new_entries: continue

            # TODO: fix probability calculation to incorporate
            # sampling w/o replacement and reflective probabilities.
            reln = instance[1]
            # Inverted probabilities
            p_mi = I
            p_ei = E * len(fills) * len(instances)
            p_ri = R[reln] * len(R)
            # Weights
            mention_weight = p_ei/p_mi
            entity_weight = 1.
            relation_weight = p_ei/p_ri

            new_entries[(instance[0], instance[2])] = instance + (mention_weight, entity_weight, relation_weight)

            if not condition(): break
        if not condition(): break
        logger.debug("Currently at %d entries", len(new_entries))
    logger.info("Done with %d entries", len(new_entries))

    return sorted(new_entries.values())

def sample_by_mention(entries, n):
    relations = [row for row in entries if is_reln(row[1])]
    true_relations = [row for row in relations if row[-1] == "1.0"]
    false_relations = [row for row in relations if row[-1] == "0.0"]
    R, T, F = len(relations), len(true_relations), len(false_relations),
    true_relations = [row + [2*T/R, 0., 0.] for row in sample(true_relations, int(n/2))]
    false_relations = [row + [2*F/R, 0., 0.] for row in sample(false_relations, int(n/2))]
    relations = true_relations + false_relations
    return relations

def reweight(types, entries, new_entries, scheme="entity"):
    """
    Compute weights for @new_entries, using @entries to compute probability scores.
    """
    # Construct an entity-centric table to sample from.
    links = {}
    entities = defaultdict(lambda: defaultdict(list))
    relations = defaultdict(list)

    # Summary statistics
    for row in entries:
        subj, relation, obj = row[:3]
        if relation in TYPES:
            continue
        if relation == "link":
            links[subj] = obj
        elif relation == "canonical_mention":
            links[subj] = links[obj]
        else:
            subj_, obj_ = links[subj], links[obj]

            row = normalize(types, row) # Normalize every entry before adding it here.
            relation = row[1]
            entities[subj_][(relation,obj_)].append(tuple(row))
            relations[relation].append(tuple(row))
    E, F, I = len(entities), sum(len(fills) for fills in entities.values()), sum(len(instances) for fills in entities.values() for instances in fills.values())
    I_ = sum(len(mentions) for mentions in relations.values())
    assert I == I_, "Discrepancy in relation, entity counts."

    # Compute observed_relations
    observed_relations = Counter(row[1] for row in new_entries if is_reln(row[1]))
    num_entries = sum(observed_relations.values())

    logger.info("Found at %d entities, %d fills, %d instances split over %d relations", E, F, I, len(relations))

    MW, EW, RW = 5, 6, 7

    new_entries_ = []
    for row in new_entries:
        assert len(row) == 8 # subj, reln, obj, prov, conf, mw, ew, rw
        subj, relation, obj = row[:3]

        if is_reln(relation):
            subj_, obj_ = links[subj], links[obj]

            p_mi = I
            p_ei = E * len(entities[subj_]) * len(entities[subj_][relation, obj_])
            p_ri = len(relations[relation]) * len(relations)
            q_ri = len(relations[relation]) * num_entries / observed_relations[relation]

            if scheme == "entity":
                row[MW] = p_ei / p_mi
                row[EW] = 1.
                row[RW] = p_ei / p_ri
            elif scheme == "relation":
                row[MW] = q_ri / p_mi
                row[EW] = q_ri / p_ei
                row[RW] = q_ri / p_ri
            else:
                raise ValueError("invalid scheme")
            new_entries_.append(row)

    return new_entries_

def do_sample(args):
    """
    entity link -> [mentions]
    - sample entities
        - sample fills
            - sample mentions
    """
    random.seed(args.seed)

    # Read input
    reader = csv.reader(args.input, delimiter = "\t")
    mentions, canonical_mention, links, relations = parse_input(reader)
    entries = mentions + canonical_mention + links + relations
    old_entries = [parse_input(csv.reader(f, delimiter = "\t"))[-1] for f in args.old_entries]
    types = {r[0]: r[1] for r in mentions}

    if args.by_mention:
        relations = sample_by_mention(entries, args.num_entries)
    elif args.by_relation:
        relations = sample_by_relation(types, entries, args.num_entries, old_entries)
    else:
        relations = sample_by_entity(types, entries, args.num_entries, args.per_entity, old_entries)
    logger.info("Sampled %d relations", len(relations))

    relations = list(map_relations(mentions, relations))
    mentions = set(m for row in relations for m in [row[0], row[2]])
    mentions.update(row[2] for row in entries if row[1] == "canonical_mention" and row[0] in mentions)
    docs = set(parse_prov(row[3])[0] for row in relations)
    logger.info("Touches %d mentions + canonical-mentions from %d documents", len(mentions), len(docs))

    # Nones are for sampling weights.
    mentions = [row + [None, None, None] for row in entries if row[0] in mentions and not is_reln(row[1])]

    # Reconstruct output: collect all mentions, links, canonical mentions and relations.
    writer = csv.writer(args.output, delimiter="\t")
    for entry in mentions + relations:
        writer.writerow(entry)

def do_reweight(args):
    """
    entity link -> [mentions]
    - sample entities
        - sample fills
            - sample mentions
    """
    # Read input
    reader = csv.reader(args.reference, delimiter = "\t")
    mentions, canonical_mention, links, relations = parse_input(reader)
    entries = mentions + canonical_mention + links + relations
    types = {r[0]: r[1] for r in mentions}

    reader = csv.reader(args.input, delimiter = "\t")
    new_entries = sum(parse_input(reader), [])

    if args.by_relation:
        scheme = "relation"
    else:
        scheme = "entity"

    relations = reweight(types, entries, new_entries, scheme)
    # Don't need to do map because new_entries is ok
    mentions = set(m for row in relations for m in [row[0], row[2]])
    mentions.update(row[2] for row in entries if row[1] == "canonical_mention" and row[0] in mentions)
    docs = set(parse_prov(row[3])[0] for row in relations)
    logger.info("Touches %d mentions + canonical-mentions from %d documents", len(mentions), len(docs))
    # Nones are for sampling weights.
    mentions = [row + [None, None, None] for row in entries if row[0] in mentions and not is_reln(row[1])]

    # Reconstruct output: collect all mentions, links, canonical mentions and relations.
    writer = csv.writer(args.output, delimiter="\t")
    for entry in mentions + relations:
        writer.writerow(entry)

def do_make_task(args):
    """
    Build a table of documents and attach mentions and relations appropriately.
    """
    reader = csv.reader(args.input, delimiter = "\t")

    documents = defaultdict(lambda: {"mentions": {}, "relations":[]})
    mention_map = {}

    for row in reader: # Data is always cleaned.
        subj, relation, obj, prov, confidence, mention_weight, entity_weight, relation_weight = row

        if relation in TYPES: # new mention!
            assert subj not in mention_map, "Seeing a duplicate mention definition!?: {}".format(row)
            doc_id, begin, end = parse_prov(prov)

            mention_map[subj] = doc_id
            mentions = documents[doc_id]["mentions"]

            mentions[subj] = {
                "id": subj,
                "gloss": obj,
                "type": relation,
                "doc_char_begin": begin,
                "doc_char_end": end
                }

        elif relation == "canonical_mention":
            doc_id = mention_map[subj]
            mentions = documents[doc_id]["mentions"]

            if subj not in mentions or obj not in mentions:
                logger.warning("Couldn't find subject/object for canonical_mention: %s", row)
                continue
            other = mentions[obj]
            mentions[subj]["entity"] = {
                "id": other["id"],
                "gloss": other["gloss"],
                "link": other["link"],
                "doc_char_begin": other["doc_char_begin"],
                "doc_char_end": other["doc_char_end"],
                }

        elif relation == "link":
            doc_id = mention_map[subj]
            mentions = documents[doc_id]["mentions"]
            if subj not in mentions:
                logger.warning("Couldn't find subject for link: %s", row)
                continue
            mentions[subj]["link"] = obj

        else:
            doc_id, begin, end = parse_prov(prov)

            mentions = documents[doc_id]["mentions"]
            relations = documents[doc_id]["relations"]

            if subj not in mentions or obj not in mentions:
                logger.warning("Couldn't find subject/object for relation: %s", row)
                continue

            relations.append({
                "subject": mentions[subj],
                "relation": relation,
                "object": mentions[obj],
                "doc_char_begin": begin,
                "doc_char_end": end,
                "confidence": float(confidence),
                "mention_weight": float(mention_weight),
                "entity_weight": float(entity_weight),
                "relation_weight": float(relation_weight),
                })
    logger.info("Using %d documents", len(documents))

    ensure_dir(args.output)
    for doc_id, doc in documents.items():
        relations = doc['relations']
        doc['doc_id'] = doc_id
        doc['sentences'] = query_doc(doc_id, args.sentence_table)
        assert len(doc['sentences']) > 0, "Couldn't find document {}".format(doc_id)
        for relation in relations:
            doc['relations'] = [relation]
            b1, e1 = relation['subject']['doc_char_begin'], relation['subject']['doc_char_end']
            b2, e2 = relation['object']['doc_char_begin'], relation['object']['doc_char_end']

            logger.info("Saving %s with %d relations", doc_id, len(doc['relations']))
            with open(os.path.join(args.output, "{}-{}-{}-{}-{}.json".format(doc['doc_id'], b1, e1, b2, e2)), 'w') as f:
                json.dump(doc, f)

def score_instance(ref_kb, input_kb):
    """
    Score instance level scores.
    """
    input_mentions = {r.subj: r.prov for r in input_kb.mentions}
    ref_mentions = {r.subj: r.prov for r in ref_kb.mentions}

    I = {(input_mentions[r.subj], r.reln, input_mentions[r.obj]): r for r in input_kb.relations}
    Ic = {(ref_mentions[r.subj], r.reln, ref_mentions[r.obj]): r for r in ref_kb.relations if float(r.score) == 1.}

    correct = sum(sum((r.iw or 1.0) / (s.iw or 1.0) for r in [I[k]]) for k, s in Ic.items()  if k in I)
    guessed = sum((r.iw or 1.0) for r in I.values())
    total = sum((s.iw or 1.0) for s in Ic.values())

    P = correct / guessed
    R = correct / total
    F1 = 2 * P * R / (P + R)

    return P, R, F1

def score_relation(ref_kb, input_kb):
    """
    Score entity level scores.
    """
    ref_provs = set(r.prov for r in ref_kb.mentions)
    ref_mentions = {r.subj: r.prov for r in ref_kb.mentions}
    input_mentions = {r.subj: r.prov for r in input_kb.mentions if r.prov in ref_provs}

    # Create a relation table
    I, Ic = defaultdict(dict), defaultdict(dict)
    for r in input_kb.relations:
        if r.prov in ref_provs:
            I[r.reln][(input_mentions[r.subj], r.reln, input_mentions[r.obj])] = r
    for s in ref_kb.relations:
        if float(s.score) == 1.:
            Ic[s.reln][(ref_mentions[s.subj], s.reln, ref_mentions[s.obj])] = s

    P, R, F1 = {}, {}, {}
    for reln in I:
        i = I[reln]
        ic = Ic[reln]

        correct = sum( sum((r.rw or 1.0) / (s.rw or 1.0) for r in [i[k]]) for k, s in ic.items()  if k in i)
        guessed = sum((r.rw or 1.0) for r in i.values())
        total = sum((s.rw or 1.0) for s in ic.values())

        P[reln] = (correct / guessed) if (correct > 0.) else 0.
        R[reln] = (correct / total) if (correct > 0.) else 0.
        F1[reln] = 2 * P[reln] * R[reln] / (P[reln] + R[reln]) if (correct > 0.) else 0.

        print(reln, P[reln], R[reln], F1[reln],)

    mP = sum(P.values())/len(P)
    mR = sum(R.values())/len(R)
    mF1 = sum(F1.values())/len(F1)

    return mP, mR, mF1

def score_entity(ref_kb, input_kb):
    """
    Score entity level scores.
    """
    input_links = {r.subj: r.obj for r in input_kb.links}
    ref_links = {r.subj: r.obj for r in ref_kb.links}
    for r in input_kb.canonical_mentions:
        input_links[r.subj] = input_links[r.obj]
    for r in ref_kb.canonical_mentions:
        ref_links[r.subj] = ref_links[r.obj]
    input_links = {r.subj: r.obj for r in input_kb.links}
    ref_links = {r.subj: r.obj for r in ref_kb.links}


    input_mentions = {r.subj: input_links[r.subj] for r in input_kb.mentions}
    ref_mentions = {r.subj: ref_links[r.subj] for r in ref_kb.mentions}

    # Create a relation table
    I, Ic = defaultdict(dict), defaultdict(dict)
    for r in input_kb.relations:
        I[input_mentions[r.subj]][r.reln, input_mentions[r.obj]] = r
    for s in ref_kb.relations:
        I[ref_mentions[s.subj]][s.seln, ref_mentions[s.obj]] = s

    P, R, F1 = {}, {}, {}
    for entity in I:
        i = I[entity]
        ic = Ic[entity]

        correct = sum( sum((r.ew or 1.0) / (s.ew or 1.0) for r in [i[k]]) for k, s in ic.items()  if k in i)
        guessed = sum((r.ew or 1.0) for r in i.values())
        total = sum((s.ew or 1.0) for s in ic.values())

        P[entity] = (correct / guessed) if (correct > 0.) else 0.
        R[entity] = (correct / total) if (correct > 0.) else 0.
        F1[entity] = 2 * P[entity] * R[entity] / (P[entity] + R[entity]) if (correct > 0.) else 0.

        print(entity, P[entity], R[entity], F1[entity],)

    mP = sum(P.values())/len(P)
    mR = sum(R.values())/len(R)
    mF1 = sum(F1.values())/len(F1)

    return mP, mR, mF1

def do_score(args):
    # Read input
    input_kb = KnowledgeBase(*parse_input(csv.reader(args.input, delimiter = "\t")))
    ref_kb = KnowledgeBase(*parse_input(csv.reader(args.refs, delimiter = "\t")))

    if args.mode == "instance":
        print(score_instance(ref_kb, input_kb))
    elif args.mode == "relation":
        print(score_relation(ref_kb, input_kb))
    elif args.mode == "entity":
        print(score_entity(ref_kb, input_kb))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Saves document to file in json format.')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('score', help='Score instances')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), help="Input M-file")
    command_parser.add_argument('-r', '--refs', type=argparse.FileType('r'), help="Input M-file")
    command_parser.add_argument('-m', '--mode', choices=["entity", "relation", "instance"], help="Input M-file")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="data/pooled-eval.tsv", help="A path to a folder to save output.")
    command_parser.set_defaults(func=do_score)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Different entity sampling schemes.
"""

import random
import logging
from collections import Counter, defaultdict

import numpy as np

from .defs import RELATIONS, INVERTED_RELATIONS, TYPES
from .db import query_docs, query_entities, query_entity_docs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# = Generic utilities

def sample_without_replacement(lst, n, weights=None):
    """
    Sample @n elements from @lst randomly.
    """
    if weights:
        elems, _ = zip(*sorted(zip(lst, weights), key=lambda t: random.random()**t[1])[:n])
        return elems
    else:
        return sorted(lst, key=lambda _: random.random())[:n]

def normalize_probs(lst):
    total = sum(lst)
    return [x/total for x in lst]

def get_queries(docs):
    """
    Retreives all the entities in said documents.
    """
    return Counter({entity: count for entity, count in query_entities(docs)})

# = Document sample routines.

def sample_docs_uniform(corpus_id, sentence_table, num_docs):
    docs = set(d for d, in query_docs(corpus_id, sentence_table=sentence_table))
    logger.info("Sampling %d documents from %d", num_docs, len(docs))
    return sample_without_replacement(docs, num_docs)

def sample_docs_entity(corpus_id, sentence_table, mention_table, per_entity, num_docs, is_uniform=True, fudge=1):
    # Sample 0.2 * n documents.
    docs = set(d for d, in query_docs(corpus_id, sentence_table=sentence_table))
    logger.info("Sampling %d documents from %d", num_docs, len(docs))

    doc_collection = set(sample_without_replacement(docs, int(.2 * num_docs)))
    logger.info("Seeding with %d documents", len(doc_collection))

    # Find all mentions and hence links in these documents.
    seed_entities = list(query_entities(sorted(doc_collection), mention_table=mention_table))
    logger.info("Found %d entities", len(seed_entities))

    # Create a table with these seed entities, and use them in querying.
    doc_map = query_entity_docs(seed_entities)

    entities, probs = [], []
    for entity, docs in doc_map.items():
        if len(docs) > 1.:
            entities.append(entity)
            probs.append(np.log(len(docs))**(fudge))
    assert len(entities) > 0
    probs = normalize_probs(probs)
    #print(Counter(dict(zip(entities,probs))).most_common(10))

    # Proceed to add entities
    while len(doc_collection) < num_docs and len(entities) > 0:
        # Sample an entity.
        if is_uniform:
            idx = np.random.choice(len(entities))
        else:
            idx = np.random.choice(len(entities), p=probs)

        entity, prob = entities.pop(idx), probs.pop(idx)
        probs = normalize_probs(probs) # renormalize distribution
        #print(Counter(dict(zip(entities,probs))).most_common(10))

        logger.debug("Searching for %s %.4f", entity, prob)
        docs_ = set(doc_map[entity])
        docs_.difference_update(doc_collection)
        # Measure how many to sample.
        m = min(num_docs - len(doc_collection), per_entity)
        doc_collection.update(sample_without_replacement(docs_, m))
        logger.debug("Now at %s", len(doc_collection))
    assert len(doc_collection) == num_docs, "Couldn't find 'n' documents!"
    return doc_collection

def sample_docs(corpus_id, sentence_table, mention_table, mode, num_docs, per_entity=4, fudge=1):
    """
    Sample documents according to mode.
    """
    if mode == "uniform":
        return sample_docs_uniform(corpus_id, sentence_table, num_docs)
    elif mode == "entity_uniform":
        return sample_docs_entity(corpus_id, sentence_table, mention_table, per_entity, num_docs, is_uniform=True, fudge=fudge)
    elif mode == "entity":
        return sample_docs_entity(corpus_id, sentence_table, mention_table, per_entity, num_docs, is_uniform=False, fudge=fudge)
    else:
        raise ValueError("Invalid sampling mode: " + mode)

# = Instance sampling routines
def map_relations(entries, relations):
    return (entries.normalize_relation(r) for r in relations)

def get_relation_pairs(old_entries):
    ret = set()
    for r in old_entries.relations:
        ret.add(r.pair)
        if r.reln in INVERTED_RELATIONS:
            ret.add(r.inv_pair)
    return ret

def sample_by_relation(entries, num_samples, old_entries=None):
    """
    Sample from @num_samples entries from @entries in a way that keeps
    the relation distribution as uniform as possible.

    @types is a mapping from entry to type.
    @old_entries are existing entries that should be ignored when sampling.
    """
    old_pairs = get_relation_pairs(old_entries) if old_entries is not None else []

    # Populate population table.
    population = defaultdict(list)
    for row in entries.relations:
        if row.pair in old_pairs: continue

        row = entries.normalize_relation(row) # Normalize every entry before adding it here.
        reln = row.reln
        population[reln].append(row)
    I = sum(len(instances) for instances in population.values()) # Count the number of instances
    logger.info("Found at %d instances split over %d relations", I, len(population))

    # Build a list of samples (one for every (subj, obj) pair).
    samples = {}

    # Sort relations by decreasing frequency.
    for i, (relation, instances) in enumerate(sorted(population.items(), key=lambda t:(len(t[1]),t[0]))):
        remaining_samples = num_samples - len(samples)
        remaining_relations = len(population) - i
        per_relation = int(remaining_samples / remaining_relations)

        # Don't double-sample an instance.
        instances = [instance for instance in instances if (instance.pair) not in samples]

        for instance in sample_without_replacement(instances, per_relation):
            weight = 1.0 # TODO: figure out.
            samples[instance.pair] = instance._replace(weight=weight)

        logger.info("Currently at %s (%d/%d) and %d instances", relation, i, len(population), len(samples))
    logger.info("Done with %d instances", len(samples))
    return sorted(samples.values())

def sample_by_entity(entries, num_entries, per_entity=10, old_entries=None):
    old_pairs = get_relation_pairs(old_entries) if old_entries is not None else []

    # Construct an entity-centric table to sample from.
    population = defaultdict(lambda: defaultdict(list))
    for row in entries.relations:
        if row.pair in old_pairs: continue # skip old_entries
        subj_, obj_ = entries.get_link(row.subj), entries.get_link(row.obj)
        # TODO: invert relations?
        row = entries.normalize_relation(row)
        population[subj_][(row.reln,obj_)].append(row)
    E, F, I = len(population), sum(len(fills) for fills in population.values()), sum(len(instances) for fills in population.values() for instances in fills.values())
    logger.info("Found at %d entities, %d fills and %d instances", E, F, I)

    samples = {}
    condition = lambda: len(samples) < num_entries

    # Sample (without replacement) uniformly from entities
    for entity in sorted(sorted(population.keys()), key=lambda *args: random.random()):
        fills = population[entity]
        Z = sum(len(vs) for vs in fills.values())
        instances, weights = zip(*[(i, len(vs)/Z) for vs in fills.values() for i in vs])

        for instance in sample_without_replacement(instances, per_entity, weights):
            if instance.pair in samples: continue # This really shouldn't happen, unless you predict different relations for the same pair.
            weight = 1.0 # TODO: figure out

            samples[instance.pair] = instance._replace(weight=weight)
            if not condition(): break
        if not condition(): break
        logger.debug("Currently at %d instances over %d entities", sum(len(vs) for vs in samples.values()), len(samples))
    logger.info("Done with %d instances over %d entities", sum(len(vs) for vs in samples.values()), len(samples))

    return sorted(samples.values())

def sample_by_instance(entries, num_samples, old_entries=None):
    """
    Sample @num_sample entries from @entries, uniformly at random over the instances.

    @_ is a mapping from entry to type that is not used.
    @old_entries are existing entries that should be ignored when sampling.
    """
    old_pairs = get_relation_pairs(old_entries) if old_entries is not None else []

    population = [row for row in entries.relations if row.pair not in old_pairs]
    sample = sample_without_replacement(population, num_samples)
    return sample

def sample_by_balanced_instances(entries, num_samples):
    true_instances = [row for row in entries.relations if row.score == 1.0]
    false_instances = [row for row in entries.relations if row.score == 0.0]

    T, F = len(true_instances), len(false_instances)
    R = T + F

    true_sample = [row._replace(weight=2*T/R) for row in sample_without_replacement(true_instances, int(np.ceil(num_samples/2)))]
    false_sample = [row._replace(weight=2*F/R) for row in sample_without_replacement(false_instances, int(np.floor(num_samples/2)))]
    sample = true_sample + false_sample
    return sample

# def reweight(types, entries, new_entries, scheme="entity"):
#     """
#     Compute weights for @new_entries, using @entries to compute probability scores.
#     """
#     # Construct an entity-centric table to sample from.
#     links = {}
#     entities = defaultdict(lambda: defaultdict(list))
#     relations = defaultdict(list)
# 
#     # Summary statistics
#     for row in entries:
#         subj, relation, obj = row[:3]
#         if relation in TYPES:
#             continue
#         if relation == "link":
#             links[subj] = obj
#         elif relation == "canonical_mention":
#             links[subj] = links[obj]
#         else:
#             subj_, obj_ = links[subj], links[obj]
# 
#             row = normalize(types, row) # Normalize every entry before adding it here.
#             relation = row[1]
#             entities[subj_][(relation,obj_)].append(tuple(row))
#             relations[relation].append(tuple(row))
#     E, F, I = len(entities), sum(len(fills) for fills in entities.values()), sum(len(instances) for fills in entities.values() for instances in fills.values())
#     I_ = sum(len(mentions) for mentions in relations.values())
#     assert I == I_, "Discrepancy in relation, entity counts."
# 
#     # Compute observed_relations
#     observed_relations = Counter(row[1] for row in new_entries if is_reln(row[1]))
#     num_entries = sum(observed_relations.values())
# 
#     logger.info("Found at %d entities, %d fills, %d instances split over %d relations", E, F, I, len(relations))
# 
#     MW, EW, RW = 5, 6, 7
# 
#     new_entries_ = []
#     for row in new_entries:
#         assert len(row) == 8 # subj, reln, obj, prov, conf, mw, ew, rw
#         subj, relation, obj = row[:3]
# 
#         if is_reln(relation):
#             subj_, obj_ = links[subj], links[obj]
# 
#             p_mi = I
#             p_ei = E * len(entities[subj_]) * len(entities[subj_][relation, obj_])
#             p_ri = len(relations[relation]) * len(relations)
#             q_ri = len(relations[relation]) * num_entries / observed_relations[relation]
# 
#             if scheme == "entity":
#                 row[MW] = p_ei / p_mi
#                 row[EW] = 1.
#                 row[RW] = p_ei / p_ri
#             elif scheme == "relation":
#                 row[MW] = q_ri / p_mi
#                 row[EW] = q_ri / p_ei
#                 row[RW] = q_ri / p_ri
#             else:
#                 raise ValueError("invalid scheme")
#             new_entries_.append(row)
# 
#     return new_entries_

def sample_instances(mode, candidates, num_samples, old_entries=None, per_entity=None):
    """
    Sample relations according to mode.
    """

    if mode == "instance":
        return sample_by_instance(candidates, num_samples, old_entries=old_entries)
    elif mode == "entity":
        return sample_by_entity(candidates, num_samples, per_entity=per_entity, old_entries=old_entries)
    elif mode == "relation":
        return sample_by_relation(candidates, num_samples, old_entries=None)
    elif mode == "balanced":
        return sample_by_balanced_instances(candidates, num_samples)
    else:
        raise ValueError("Invalid sampling mode: " + mode)

    return []

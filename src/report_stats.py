#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Computes statistics on how various sampling schemes compare.
"""

import csv
import sys
import json
import logging
from collections import Counter, defaultdict

import numpy as np

from kbpo.sampling import get_queries, sample_docs, sample_instances
from kbpo.entry import Entry, MFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def load_counts(fstream):
    return Counter({entity: float(count) for entity, count in  csv.reader(fstream, delimiter="\t")})

def compute_logZ(counts):
    counts = list(counts.values())
    return np.logaddexp.reduce(np.log(counts))

def normalize_entity(entity):
    """
    Apply same transform as for the histogram. (taken from postgres function)
    """
    return entity.lower().translate(str.maketrans(' []{}%+|?=<>\'"\\/', '________________'))

def test_compute_logZ():
    c = Counter()
    c['a'] = 1
    c['b'] = 2
    c['c'] = 3
    logZ = np.log(sum(c.values()))

    logZ_ = compute_logZ(c)
    assert np.allclose(logZ_, logZ)

def compute_entropy(counts, sample):
    logZ = compute_logZ(counts)
    return np.log([counts[q] for q in sample]).mean() - logZ

def test_compute_entropy():
    c = Counter()
    c['a'] = 1
    c['b'] = 2
    c['c'] = 3
    sample = ['a', 'a', 'c']
    entropy = 1./3. * (np.log(1./6.) + np.log(1./6.) + np.log(3./6.))

    entropy_ = compute_entropy(c, sample)
    assert np.allclose(entropy, entropy_)

def do_ldc(args):
    logger.info("loading data...")
    # Load entity-doc frequency counts.
    counts = load_counts(args.counts)
    logger.info("done")

    logger.info("loading queries...")
    # Get the list of query entities
    queries = [normalize_entity(line.strip()) for line in args.input]
    queries = [q for q in queries if q in counts]
    logger.info("done")


    # Translate each of these entities into entity frequencies.
    logger.info("saving output...")
    obj = {}
    obj['mode'] = "ldc"
    obj['frequencies'] = [[counts[q] for q in queries]]
    obj['entropy'] = [compute_entropy(counts, queries)]
    logger.info("entropy: %.2f", obj['entropy'][-1])
    logger.info("done")

    json.dump(obj, args.output)

def do_exhaustive(args):
    logger.info("loading data...")
    # Load entity-doc frequency counts.
    counts = load_counts(args.counts)
    logger.info("done")

    obj = {}
    obj['mode'] = "exhaustive:{}:{:.2f}".format(args.mode, args.fudge)
    obj['frequencies'] = []
    obj['crosslinks'] = []
    obj['entropy'] = []
    logger.info("sampling queries...")
    for i in range(args.num_samples):
        logger.info("sample %d", i)

        queries = get_queries(sample_docs(args.corpus_id, args.sentence_table, args.mention_table, args.mode, args.num_docs, fudge=args.fudge))
        queries = {normalize_entity(q): c for q, c in queries.items() if normalize_entity(q) in counts}
        obj['frequencies'].append([counts[q] for q in queries])
        obj['crosslinks'].append([(counts[q], c) for q, c in queries.items()])
        obj['entropy'].append(compute_entropy(counts, queries))

        logger.info("entropy: %.2f", obj['entropy'][-1])
    logger.info("done")

    json.dump(obj, args.output)

def do_selective(args):
    logger.info("loading data...")
    # Load entity-doc frequency counts.
    counts = load_counts(args.counts)
    def bin_entity(entity):
        if entity not in counts: return None
        elif counts[entity] <= 3: return "low"
        elif counts[entity] <= 100: return "med"
        else: return "high"

    entries = MFile.from_stream(csv.reader(args.input, delimiter='\t'))
    logger.info("Loaded submissions file with %d entries", len(entries.relations))
    logger.info("done")

    samples = []
    logger.info("sampling queries...")
    instance_frequency, pair_frequency, relation_frequency, cluster_frequency = Counter(), Counter(), Counter(), defaultdict(list)
    for i in range(args.num_samples):
        logger.info("sample %d", i)
        instances = sample_instances(args.mode, entries, args.num_entries, old_entries=None, per_entity=args.per_entity)
        print(len(instances))

        # Get relations from the instances
        clusters = Counter()
        for instance in instances:
            subj = normalize_entity(entries.get_mention(instance.subj))
            obj = normalize_entity(entries.get_mention(instance.obj))
            reln = instance.reln

            instance_frequency[bin_entity(subj)] += 1
            #instance_frequency[bin_entity(obj)] += 1
            pair_frequency["{} {}".format(bin_entity(subj), bin_entity(obj))] += 1
            relation_frequency[reln] += 1

            clusters[subj] += 1
            #clusters[obj] += 1
        for entity, count in clusters.items():
            cluster_frequency[bin_entity(entity)].append(count)
        samples.append([instance_frequency, pair_frequency, relation_frequency, cluster_frequency])
    logger.info("done")

    obj = {
        "mode": "selective:{}".format(args.mode),
        "samples": args.num_samples,
        "instance_frequency": instance_frequency,
        "pair_frequency": pair_frequency,
        "relation_frequency": relation_frequency,
        "cluster_frequency": cluster_frequency,
        }
    json.dump(obj, args.output)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Computes statistics for different sampling schemes.')
    parser.add_argument('-c', '--counts', type=argparse.FileType('r'), default="data/analysis/2015.counts", help="Path to past year entity-count distributions.")

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('ldc', help='Statistics on the LDC query distribution')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default="data/analysis/2015.queries", help="Path to past year query distributions.")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="ldc.json", help="An output object with computed statistics")
    command_parser.set_defaults(func=do_ldc)

    command_parser = subparsers.add_parser('exhaustive', help='Statistics for the exhaustive sampling methods')
    command_parser.add_argument('-ct', '--corpus-id', type=str, default="2015", help="Mention table to use")
    command_parser.add_argument('-mt', '--mention-table', type=str, default="mention", help="Mention table to use")
    command_parser.add_argument('-st', '--sentence-table', type=str, default="sentence", help="Sentence table")

    command_parser.add_argument('-m', '--mode', choices=["uniform", "entity_uniform", "entity"], default="uniform", help="Which sampling scheme?")
    command_parser.add_argument('-n', '--num-docs', type=int, default=200, help="Number of documents to exhaustively sample")
    command_parser.add_argument('-p', '--per-entity', type=int, default=4, help="Number of documents to sample per entity")
    command_parser.add_argument('-f', '--fudge', type=float, default=1., help="Number of documents to sample per entity")

    command_parser.add_argument('-s', '--seed', type=int, default=42, help="Random seed to select documents.")
    command_parser.add_argument('-ns', '--num-samples', type=int, default=10, help="Number of samples")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="exhaustive.json", help="An output object with computed statistics")
    command_parser.set_defaults(func=do_exhaustive)

    command_parser = subparsers.add_parser('selective', help='Statistics for the selective sampling methods')
    command_parser.add_argument('-ct', '--corpus_id', type=str, default="2015", help="Mention table to use")
    command_parser.add_argument('-mt', '--mention-table', type=str, default="mention", help="Mention table to use")
    command_parser.add_argument('-st', '--sentence-table', type=str, default="sentence", help="Sentence table")

    command_parser.add_argument('-m', '--mode', choices=["instance", "entity", "relation"], default="instance", help="Which sampling scheme?")
    command_parser.add_argument('-n', '--num-entries', type=int, default=1000, help="Number of instances to exhaustively sample")
    command_parser.add_argument('-p', '--per-entity', type=int, default=5, help="Number of documents to sample per entity")

    command_parser.add_argument('-s', '--seed', type=int, default=42, help="Random seed to select documents.")
    command_parser.add_argument('-ns', '--num-samples', type=int, default=10, help="Number of samples")
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default="data/analysis/2015.submission", help="Path to past year submission.")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="selective.json", help="An output object with computed statistics")
    command_parser.set_defaults(func=do_selective)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

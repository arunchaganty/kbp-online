#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyzes the sampling behavior of KBPO.
"""
import csv 
import sys
import logging

from collections import namedtuple, defaultdict, Counter

import numpy as np
from tqdm import tqdm

from kbpo import db
from kbpo import distribution as D
from kbpo.sample_util import sample_with_replacement, sample_without_replacement

logger = logging.getLogger(__name__)

def construct_example(samples):
    """
    Joins given samples in the database and pulls out sentences with
    mentions (as strings) to render.
    """
    Row = namedtuple("Row", ["doc_id", "gloss", "span", "subject", "object"])
    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""CREATE TEMPORARY TABLE _samples (
                    doc_id TEXT NOT NULL,
                    subject INT4RANGE NOT NULL,
                    object INT4RANGE NOT NULL
                    ) ON COMMIT DROP;""")
            db.execute_values(cur, "INSERT INTO _samples VALUES %s", [
                (doc_id, db.Int4NumericRange(*subject), db.Int4NumericRange(*object_)) for doc_id, subject, object_ in samples
                ])

            ret = []
            for row in db.select(r"""
                SELECT x.doc_id, gloss, span, subject, object
                FROM _samples x
                JOIN sentence s ON (x.doc_id = s.doc_id AND x.subject <@ s.span AND x.object <@ s.span)
                """):
                elem = Row(row.doc_id, row.gloss, (row.span.lower, row.span.upper), (row.subject.lower, row.subject.upper), (row.object.lower, row.object.upper))
                ret.append(elem)
    return ret

def get_entity_relation(corpus_tag, submission_id=None):
    """
    Mapping from (doc_id, subject, object) -> subject_entity, subject_type, relation, object_entity, object_type
    """
    where = "AND r.submission_id = %(submission_id)s" if submission_id is not None else ""

    Row = namedtuple("Row", ["subject_link", "subject_type", "object_link", "object_type", "relation"])
    ret = defaultdict(dict)
    for row in db.select("""
        SELECT r.submission_id, doc_id, subject, object, subject_type, subject_entity, object_type, object_entity, relation
        FROM submission_entity_relation r
        JOIN submission s ON (r.submission_id = s.id)
        WHERE s.corpus_tag = %(corpus_tag)s
        {where}
        """.format(where=where), corpus_tag=corpus_tag, submission_id=submission_id):
        ret[row.submission_id][(row.doc_id, (row.subject.lower, row.subject.upper), (row.object.lower, row.object.upper))] = Row(row.subject_entity, row.subject_type, row.object_entity, row.object_type, row.relation)
    return ret

def render_example(ex):
    offset = ex.span[0]
    subject = (ex.subject[0]-offset, ex.subject[1]-offset)
    object_ = (ex.object[0]-offset,  ex.object[1]-offset)
    if object_[0] < subject[0]:
        subject, object_ = object_, subject

    gloss = "{}*{}*{}^{}^{}".format(ex.gloss[:subject[0]], ex.gloss[subject[0]:subject[1]], ex.gloss[subject[1]:object_[0]], ex.gloss[object_[0]:object_[1]], ex.gloss[object_[1]:])
    return "{}:{}-{}\t{}".format(ex.doc_id, ex.span[0], ex.span[1], gloss)

def do_relation_sample(args):
    if args.distribution == "instance":
        P = D.submission_instance(args.corpus_tag, args.submission_id)
    elif args.distribution == "relation":
        P = D.submission_relation(args.corpus_tag, args.submission_id)
    elif args.distribution == "entity":
        P = D.submission_entity(args.corpus_tag, args.submission_id)
    elif args.distribution == "entity-relation":
        P = D.submission_entity_relation(args.corpus_tag, args.submission_id)
    else:
        raise ValueError("Invalid distribution type: " + args.distribution)

    for submission_id in P:
        print("= Submission: {}".format(submission_id))
        #samples = sample_with_replacement(P[submission_id], args.samples)
        samples = sample_without_replacement(P[submission_id], args.samples)
        examples = construct_example(samples)
        # Get from these samples
        for ex in examples:
            print(render_example(ex))

def do_relation_histogram(args):
    if args.distribution == "instance":
        P = D.submission_instance(args.corpus_tag, args.submission_id)
    elif args.distribution == "relation":
        P = D.submission_relation(args.corpus_tag, args.submission_id)
    elif args.distribution == "entity":
        P = D.submission_entity(args.corpus_tag, args.submission_id)
    elif args.distribution == "entity-relation":
        P = D.submission_entity_relation(args.corpus_tag, args.submission_id)
    else:
        raise ValueError("Invalid distribution type: " + args.distribution)

    T = get_entity_relation(args.corpus_tag, args.submission_id)

    for submission_id in P:
        # Map each of these instances into types
        dist = Counter()
        for key, value in P[submission_id].items():
            entry = T[submission_id][key]
            dist[entry.relation] += value

        # Aggregate by type.
        print("= Submission: {}".format(submission_id))
        # Get all of submission's output.
        # For every (predicted) relation, compute mass.
        for relation, value in dist.most_common():
            print("* {:.3f} {}".format(value, relation))
        print()

        #Xh = sample_with_replacement(P[submission_id], args.samples)
        Xh = sample_without_replacement(P[submission_id], args.samples)
        dist = Counter()
        for key in Xh:
            entry = T[submission_id][key]
            dist[entry.relation] += 1

        # Aggregate by type.
        print("= Submission (sample): {}".format(submission_id))
        # Get all of submission's output.
        # For every (predicted) relation, compute mass.
        for relation, value in dist.most_common():
            print("* {:.3f} {}".format(value, relation))
        print()
        # TODO: save to a JSON file.

# TODO: plot relation histogram.

def do_entity_histogram(args):
    if args.distribution == "instance":
        P = D.submission_instance(args.corpus_tag, args.submission_id)
    elif args.distribution == "relation":
        P = D.submission_relation(args.corpus_tag, args.submission_id)
    elif args.distribution == "entity":
        P = D.submission_entity(args.corpus_tag, args.submission_id)
    elif args.distribution == "entity-relation":
        P = D.submission_entity_relation(args.corpus_tag, args.submission_id)
    else:
        raise ValueError("Invalid distribution type: " + args.distribution)

    T = get_entity_relation(args.corpus_tag, args.submission_id)

    for submission_id in P:
        # Map each of these instances into types
        dist = Counter()
        for key, value in P[submission_id].items():
            entry = T[submission_id][key]
            dist[entry.relation] += value

        # Aggregate by type.
        print("= Submission: {}".format(submission_id))
        # Get all of submission's output.
        # For every (predicted) relation, compute mass.
        for relation, value in dist.most_common():
            print("* {:.3f} {}".format(value, relation))
        print()
    # -- Plot histogram of relations.

    # -- Plot histogram of entities.

def do_compute_entity_bins(args):
    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""SELECT link_name, count
                           FROM suggested_link_frequencies
                           WHERE tag = %(corpus_tag)s
                           """.format(link_table=args.link_table, mention_table=args.mention_table), {"corpus_tag": args.corpus_tag})
            data = np.array([row.count for row in cur])

    low, med, high = np.percentile(data, 50), np.percentile(data, 90), np.percentile(data, 100)
    print("Frequency bins: low (50%) {}, medium (90%) {} and high (100%) {}".format(low, med, high))

def do_document_sample(args):
    if args.distribution == "ldc":
        # TODO: need to get LDC data and correlate it with
        # suggested_link_frequencies
        raise NotImplementedError()


    if args.distribution == "uniform":
        P = D.document_uniform(args.corpus_tag)
        docs = sample_without_replacement(P, args.samples)

    elif args.distribution == "entity":
        P0 = D.document_uniform(args.corpus_tag)
        seed_docs = sample_without_replacement(P0, args.samples // 30)
        P = D.document_entity(args.corpus_tag, seed_docs, mention_table = "suggested_mention")
        docs = seed_docs + sample_without_replacement(P, args.samples - len(seed_docs))
    else:
        raise ValueError("Invalid distribution type: " + args.distribution)

    # TODO: Use docs to identify (a) the frequency of entities found in
    # these docs and (b) the # of documents across which entities were
    # found.

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Analyzes the sampling behavior of KBPO')
    parser.add_argument('-ct', '--corpus-tag', type=str, default="kbp2016", help="Corpus to study")
    parser.add_argument('-mt', '--mention-table', type=str, default="suggested_mention", help="Mention table to use")
    parser.add_argument('-lt', '--link-table', type=str, default="suggested_link", help="Mention table to use")
    parser.add_argument('-st', '--sentence-table', type=str, default="sentence", help="Sentence table")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('compute-entity-bins', help='Constructs an entity histogram from the database')
    command_parser.set_defaults(func=do_compute_entity_bins)

    command_parser = subparsers.add_parser('document-sample', help='Draws samples from database')
    command_parser.add_argument('-s', '--submission-id', type=int, help="Submission to analyze (leave blank to analyze all)")
    command_parser.add_argument('-d', '--distribution', choices=['instance', 'relation', 'entity', 'entity-relation'], default='entity-relation', help="Distribution to sample from")
    command_parser.add_argument('-n', '--samples', default=20, help="How many samples to draw")
    command_parser.set_defaults(func=do_document_sample)


    command_parser = subparsers.add_parser('relation-sample', help='Draws samples from database')
    command_parser.add_argument('-s', '--submission-id', type=int, help="Submission to analyze (leave blank to analyze all)")
    command_parser.add_argument('-d', '--distribution', choices=['instance', 'relation', 'entity', 'entity-relation'], default='entity-relation', help="Distribution to sample from")
    command_parser.add_argument('-n', '--samples', default=20, help="How many samples to draw")
    command_parser.set_defaults(func=do_sample)

    command_parser = subparsers.add_parser('relation-histogram', help='Histogram of relations queried')
    command_parser.add_argument('-s', '--submission-id', type=int, help="Submission to analyze (leave blank to analyze all)")
    command_parser.add_argument('-d', '--distribution', choices=['instance', 'relation', 'entity', 'entity-relation'], default='entity-relation', help="Distribution to sample from")
    command_parser.add_argument('-n', '--samples', default=1000, type=int, help="How many samples to draw")
    command_parser.set_defaults(func=do_relation_histogram)

    logging.basicConfig(level=logging.DEBUG)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

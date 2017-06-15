#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyzes the sampling behavior of KBPO.
"""
import sys
import logging

from kbpo import db
from kbpo import distribution as D
from kbpo.sample_util import sample_without_replacement

logger = logging.getLogger(__name__)

def construct_example(samples):
    """
    Joins given samples in the database and pulls out sentences with
    mentions (as strings) to render.
    """
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
                elem = [row.doc_id, row.gloss, (row.span.lower, row.span.upper), (row.subject.lower, row.subject.upper), (row.object.lower, row.object.upper),]
                ret.append(elem)
    return ret

def render_example(example):
    doc_id, gloss, span, subject, object_ = example
    offset = span[0]
    subject = (subject[0]-offset, subject[1]-offset)
    object_ = (object_[0]-offset,  object_[1]-offset)
    if object_[0] < subject[0]:
        subject, object_ = object_, subject

    gloss = "{}*{}*{}^{}^{}".format(gloss[:subject[0]], gloss[subject[0]:subject[1]], gloss[subject[1]:object_[0]], gloss[object_[0]:object_[1]], gloss[object_[1]:])
    return "{}:{}-{}\t{}".format(doc_id, span[0], span[1], gloss)

def do_sample(args):
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

    for submission_id in P:
        print("= Submission: {}".format(submission_id))
        # Get all of submission's output.
        # For every (predicted) relation, compute mass.

        samples = sample_without_replacement(P[submission_id], args.samples)
        examples = construct_example(samples)
        # Get from these samples
        for ex in examples:
            print(render_example(ex))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Analyzes the sampling behavior of KBPO')
    parser.add_argument('-ct', '--corpus-tag', type=str, default="kbp2016", help="Corpus to study")
    parser.add_argument('-mt', '--mention-table', type=str, default="suggested_mention", help="Mention table to use")
    parser.add_argument('-st', '--sentence-table', type=str, default="sentence", help="Sentence table")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('sample', help='Draws samples from database')
    command_parser.add_argument('-s', '--submission-id', type=int, help="Submission to analyze (leave blank to analyze all)")
    command_parser.add_argument('-d', '--distribution', choices=['instance', 'relation', 'entity', 'entity-relation'], default='entity-relation', help="Distribution to sample from")
    command_parser.add_argument('-n', '--samples', default=20, help="How many samples to draw")
    command_parser.set_defaults(func=do_sample)

    command_parser = subparsers.add_parser('relation_histogram', help='Histogram of relations queried')
    command_parser.add_argument('-s', '--submission-id', type=int, help="Submission to analyze (leave blank to analyze all)")
    command_parser.add_argument('-d', '--distribution', choices=['instance', 'relation', 'entity', 'entity-relation'], default='entity-relation', help="Distribution to sample from")
    command_parser.set_defaults(func=do_sample)

    logging.basicConfig(level=logging.DEBUG)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import data into database
"""
import pdb
import csv
import sys
import logging

from kbpo import db
from kbpo import web_data
from kbpo.entry import MFile

logger = logging.getLogger('kbpo')
logging.basicConfig(level=logging.INFO)

def do_submission(args):
    mfile = MFile.from_stream(csv.reader(args.input, delimiter="\t"))

    with db.CONN:
        with db.CONN.cursor() as cur:
            # Create the submission
            cur.execute("""INSERT INTO submission(name, details) VALUES %s""", [(args.name, args.description)])
            cur.execute("""SELECT MAX(id) FROM submission""")
            submission_id, = next(cur)
            logger.info("Inserting submission %d", submission_id)

            mentions, links, relations = [], [], []
            for mention_id in mfile.mention_ids:
                mention_type, gloss, canonical_id = mfile.get_type(mention_id), mfile.get_gloss(mention_id), mfile.get_cmention(mention_id)
                mention_id, canonical_id = MFile.parse_prov(mention_id), MFile.parse_prov(canonical_id)
                doc_id = mention_id.doc_id
                mentions.append((submission_id, doc_id, mention_id, canonical_id, mention_type, gloss))
            for row in mfile.links:
                mention_id = MFile.parse_prov(row.subj)
                doc_id = mention_id.doc_id
                link_name = row.obj
                weight = row.weight
                links.append((submission_id, doc_id, mention_id, link_name, weight))
            for row in mfile.relations:
                subject_id = MFile.parse_prov(row.subj)
                object_id = MFile.parse_prov(row.obj)
                doc_id = subject_id.doc_id

                relation = row.reln
                provs = row.prov.split(',')
                weight = row.weight
                relations.append((submission_id, doc_id, subject_id, object_id, relation, provs, weight))

            # mentions
            db.execute_values(cur, """INSERT INTO submission_mention (submission_id, doc_id, mention_id, canonical_id, mention_type, gloss) VALUES %s """, mentions)

            # links
            db.execute_values(cur, """INSERT INTO submission_link (submission_id, doc_id, mention_id, link_name, confidence) VALUES %s """, links)

            # relations
            db.execute_values(cur, """INSERT INTO submission_relation (submission_id, doc_id, subject_id, object_id, relation, provenances, confidence) VALUES %s """, relations)

def do_responses(args):
    # TODO: symmetrize relations in input.
    web_data.parse_responses()
    web_data.update_summary()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Import data into the database')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('submission', help='import a submission as an m-file')
    command_parser.add_argument('-n', '--name', type=str, required=True, help="Name of the submission")
    command_parser.add_argument('-d', '--description', type=str, required=True, help="Description")
    command_parser.add_argument('-t', '--corpus-tag', type=str, required=True, help="Which corpus was this submission run on?")
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=sys.stdin, help="File to import")
    command_parser.set_defaults(func=do_submission)

    command_parser = subparsers.add_parser('responses', help='Process mturk responses')
    command_parser.set_defaults(func=do_responses)


    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

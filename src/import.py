#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import data into database
"""
import pdb
import csv
import sys
import logging

from kbpo import web_data
from kbpo.entry import MFile, upload_submission
from kbpo import db

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
    upload_submission(submission_id, mfile)

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

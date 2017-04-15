#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performs sanity checks on mentions data.
"""

import csv
import sys
import logging

from kbpo.entry import MFile, verify_mention_ids, verify_canonical_mentions, verify_relations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def do_validate(args):
    reader = csv.reader(args.input, delimiter='\t')
    mfile = MFile.from_stream(reader)

    # Verify that canonical mentions are correctly linked.
    mfile = verify_mention_ids(mfile)
    mfile = verify_canonical_mentions(mfile)
    mfile = verify_relations(mfile)

    writer = csv.writer(args.output, delimiter='\t')
    for row in mfile.types:
        writer.writerow(row)
    for row in mfile.links:
        writer.writerow(row)
    for row in mfile.canonical_mentions:
        writer.writerow(row)
    for row in mfile.relations:
        writer.writerow(row)

def do_debug(args):
    reader = csv.reader(args.input, delimiter='\t')
    mfile = MFile.from_stream(reader)

    writer = csv.writer(args.output, delimiter='\t')
    for row in mfile.relations:
        writer.writerow([mfile.get_link(row.subj) or mfile.get_gloss(row.subj), row.reln, mfile.get_link(row.obj) or mfile.get_gloss(row.obj), row.prov])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Process and transform entry files')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('validate', help='Performs sanity checks and corrects simple mistakes')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=sys.stdin, help="")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="")
    command_parser.set_defaults(func=do_validate)

    command_parser = subparsers.add_parser('debug', help='Prints in English')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=sys.stdin, help="")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="")
    command_parser.set_defaults(func=do_debug)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

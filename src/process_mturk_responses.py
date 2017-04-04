#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processes mturk responses to load into the appropriate evaluation_?_response tables.
"""

import sys
import logging
from kbpo import web_data
logger = logging.getLogger("kbpo")

def do_command(args):
    web_data.parse_responses()
    web_data.update_summary()

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.DEBUG)
    logger.addHandler(logging.FileHandler("kbpo.log"))

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=sys.stdin, help="")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

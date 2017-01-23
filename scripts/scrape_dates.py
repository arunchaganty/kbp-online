#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
import os
import csv
import sys
from xml.etree.ElementTree import ElementTree

def process_df(f):
    tree = ElementTree()
    tree.parse(f)

    doc_id = tree.getroot().get("id")
    post = tree.find("post")
    date, time = post.get("datetime").split("T")
    return doc_id, date

def process_nw(f):
    tree = ElementTree()
    tree.parse(f)

    doc_id = tree.getroot().get("id")
    date, time = tree.find("DATE_TIME").text.split("T")
    return doc_id, date

def do_command(args):
    writer = csv.writer(args.output, delimiter="\t")

    for root, _, files in os.walk(args.input):
        for fname in files:
            if fname.endswith("nw.xml"):
                with open(os.path.join(root,fname)) as f:
                    writer.writerow(process_nw(f))
            elif fname.endswith("df.xml"):
                with open(os.path.join(root,fname)) as f:
                    writer.writerow(process_df(f))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', type=str, default="data/LDC2015E103_TAC_KBP_2015_Tri-Lingual_Entity_Discovery_and_Linking_Evaluation_Gold_Standard_Entity_Mentions_and_Knowledge_Base_Links/data/source_docs/eng_src", help="Path to documents")
    parser.add_argument('--output', type=argparse.FileType('w'), default=sys.stdout, help="A mapping from docid to date")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)

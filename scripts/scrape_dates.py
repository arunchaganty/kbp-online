#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
import os
import re
import csv
import sys
from xml.etree.ElementTree import ElementTree

DATE_RE = re.compile(r"(\d{4})(\d{2})(\d{2})")

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
    if tree.find("DATE_TIME") is not None:
        date, time = tree.find("DATE_TIME").text.split("T")
    else:
        # Get the date from the doc_id.
        dates = DATE_RE.findall(doc_id)
        if len(dates) > 0:
            year, month, day = dates[0]
            date = "{}-{}-{}".format(year, month, day)
        else:
            date = ""
    return doc_id, date

def do_edl(args):
    writer = csv.writer(args.output, delimiter="\t")

    for root, _, files in os.walk(args.input):
        for fname in files:
            if fname.endswith("nw.xml"):
                with open(os.path.join(root,fname)) as f:
                    writer.writerow(process_nw(f))
            elif fname.endswith("df.xml"):
                with open(os.path.join(root,fname)) as f:
                    writer.writerow(process_df(f))

def do_2015(args):
    writer = csv.writer(args.output, delimiter="\t")
    assert os.path.exists(os.path.join(args.input, "nw")), "Couldn't find the nw/ directory at {}".format(args.input)
    #assert os.path.exists(os.path.join(args.input, "mpdf")), "Couldn't find the mpdf/ directory at {}".format(args.input)

    root = os.path.join(args.input, 'nw')
    for fname in os.listdir(root):
        with open(os.path.join(root, fname)) as f:
            writer.writerow(process_nw(f))

    #root = os.path.join(args.input, 'mpdf')
    #for fname in os.listdir(root):
    #    with open(os.path.join(root, fname)) as f:
    #        writer.writerow(process_df(f))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-i', '--input', type=str, default="data/LDC2015E103_TAC_KBP_2015_Tri-Lingual_Entity_Discovery_and_Linking_Evaluation_Gold_Standard_Entity_Mentions_and_Knowledge_Base_Links/data/source_docs/eng_src", help="Path to documents")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="A mapping from docid to date")

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('edl', help='Process dates for EDL corpus')
    command_parser.set_defaults(func=do_edl)

    command_parser = subparsers.add_parser('2015', help='Process dates for 2015 corpus')
    command_parser.set_defaults(func=do_2015)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

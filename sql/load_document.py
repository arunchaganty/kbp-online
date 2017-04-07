#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processes a document into the following structure for the database:
  id TEXT PRIMARY KEY,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
  title TEXT, -- Document title
  doc_date DATE, -- Document date
  doc_length INTEGER, -- Document length (useful for consistency)
  doc_digest TEXT, -- an MD5 hash of the document.
  gloss TEXT -- Raw document text
"""
import io
import os
import re
import csv
import sys
import hashlib
from xml.etree.ElementTree import ElementTree

DATE_RE = re.compile(r"(\d{4})(\d{2})(\d{2})")

import pdb
def process_doc(f):
    raw_document = f.read()
    # Get rid of the '<? xml>' line.
    doc_length = len(raw_document)
    if raw_document.startswith('<?xml version="1.0" encoding="utf-8"?>\n'):
        doc_length -= 39
    if raw_document.endswith('\n'):
        doc_length -= 1
    doc_digest = hashlib.md5(raw_document.encode('utf-8')).hexdigest()

    # Get the length of the whole document f.
    tree = ElementTree()
    tree.parse(io.StringIO(raw_document))

    doc_id = tree.getroot().get("id")

    assert tree.find("TEXT") is not None, "Document contains no text."

    gloss = tree.find("TEXT").text.strip()

    # Try to get title.
    if tree.find("HEADLINE") is not None:
        title = tree.find("HEADLINE").text.strip()
    else: # Take first line of doc.
        title = gloss[:gloss.find("\n")]
    title = re.sub("\s+", " ", title) 

    # Try to get the date.
    if tree.find("DATE_TIME") is not None:
        date, _ = tree.find("DATE_TIME").text.split("T")
    else:
        # Get the date from the doc_id.
        dates = DATE_RE.findall(doc_id)
        if len(dates) > 0:
            year, month, day = dates[0]
            date = "{}-{}-{}".format(year, month, day)
        else:
            date = ""

    gloss = ""
    return doc_id, title, date, doc_length, doc_digest, gloss

def do_process(args):
    writer = csv.writer(args.output, delimiter="\t")
    writer.writerow(["id", "title", "doc_date", "doc_length", "doc_digest", "gloss"])

    for fname in os.listdir(args.input):
        path = os.path.join(args.input, fname)
        with open(path) as f:
            writer.writerow(process_doc(f))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-i', '--input', type=str, required=True, help="Path to documents")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="A CSV file with mappings of dates")
    parser.set_defaults(func=do_process)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

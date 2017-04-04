#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export data from the database.
"""

import csv
import sys
import logging

from kbpo import db
from kbpo.entry import MFile, Entry
from kbpo.defs import TYPES,NER_MAP,ALL_RELATIONS

logger = logging.getLogger('kbpo')
logging.basicConfig(level=logging.INFO)

def do_submission(args):
    writer = csv.writer(args.output, delimiter="\t")
    with db.CONN:
        with db.CONN.cursor() as cur:
            mention_ids = set([])
            # mentions
            # TODO: put this in the db/custom cursor class
            db.register_composite('kbpo.span', cur)
            cur.execute("""
            SELECT mention_id, mention_type, gloss
            FROM submission_mention WHERE submission_id = %s
            """, [args.submission_id])
            for row in cur:
                if row.mention_type in TYPES:
                    type_ = row.mention_type
                elif row.mention_type in NER_MAP:
                    type_ = NER_MAP[row.mention_type]
                else:
                    logger.debug("skipping %s for invalid type", row)
                    continue
                mention_ids.add(row.mention_id)
                writer.writerow([MFile.to_prov(row.mention_id), type_, row.gloss, None, None])

            # canonical_mentions
            # TODO:support weights
            cur.execute("""
            SELECT mention_id, canonical_id
            FROM submission_mention WHERE submission_id = %s
            """, [args.submission_id])
            for row in cur:
                if row.mention_id not in mention_ids or row.canonical_id not in mention_ids:
                    logger.debug("skipping %s for ignored/invalid mention", row)
                    continue
                writer.writerow([MFile.to_prov(row.mention_id), 'canonical_mention', MFile.to_prov(row.canonical_id), None, None])

            # links
            cur.execute("""
            SELECT mention_id, link_name
            FROM submission_link WHERE submission_id = %s
            """, [args.submission_id])
            for row in cur:
                if row.mention_id not in mention_ids:
                    logger.debug("skipping %s for ignored/invalid mention", row)
                    continue
                writer.writerow([MFile.to_prov(row.mention_id), 'link', row.link_name, None, None])

            # relations
            # TODO: Should have a provenance!
            cur.execute("""
            SELECT subject_id, relation, object_id
            FROM submission_relation WHERE submission_id = %s
            """, [args.submission_id])
            for row in cur:
                if row.subject_id not in mention_ids or row.object_id not in mention_ids:
                    logger.debug("skipping %s for ignored/invalid mention", row)
                    continue
                writer.writerow([MFile.to_prov(row.subject_id), row.relation, MFile.to_prov(row.object_id), None, None])

def do_stanford(args):
    """
    Grabs data from the kb_evaluation table.
    """
    kb_table, mention_table, sentence_table = args.kb_table, args.mention_table, args.sentence_table

    types, cmentions, links, relations = [], [], [], []
    with db.CONN:
        with db.CONN.cursor() as cur:
            db.register_composite('kbpo.span', cur)
            # First, get the relations in a useful way.
            cur.execute("""CREATE TEMPORARY TABLE _relation AS (
            SELECT m.doc_id AS doc_id, m.sentence_id, m.id AS subject_id, (m.doc_id, m.doc_char_begin, m.doc_char_end)::SPAN AS subject_span,
                   relation,
                   n.id AS object_id, (n.doc_id, n.doc_char_begin, n.doc_char_end)::SPAN AS object_span,
                   confidence
            FROM {mention} m, {mention} n, {kb} k
            WHERE
                m.doc_id = n.doc_id AND m.sentence_id = n.sentence_id AND m.id = k.subject_id AND n.id = k.object_id
                AND m.parent_id IS NULL and n.parent_id IS NULL
                AND is_kbpo_reln(relation)
            )""".format(kb=kb_table,mention=mention_table))
            logger.info("Wrote %d rows", cur.rowcount)

            valid_mentions = set([])
            # Get all the mention information.
            cur.execute("""
            SELECT DISTINCT ON (m.doc_id, m.doc_char_begin, m.doc_char_end)
            m.doc_id, m.doc_char_begin, m.doc_char_end, m.gloss, 
            n.ner, m.best_entity, m.best_entity_score,
            n.doc_canonical_char_begin, n.doc_canonical_char_end, n.gloss AS canonical_gloss
            FROM _relation r, {mention} m, {mention} n
            WHERE r.doc_id = m.doc_id AND r.doc_id = n.doc_id AND r.sentence_id = m.sentence_id
              AND (r.subject_id = m.id OR r.object_id = m.id)
              AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
              AND is_kbpo_type(n.ner)
            """.format(mention=mention_table))
            logger.info("Found %d rows", cur.rowcount)

            for row in cur:
                if "_ENG_" not in row.doc_id: continue
                if row.ner not in NER_MAP: continue
                prov = MFile.to_prov([row.doc_id, row.doc_char_begin, row.doc_char_end])
                canonical_prov = MFile.to_prov([row.doc_id, row.doc_canonical_char_begin, row.doc_canonical_char_end])
                valid_mentions.add(prov)
                valid_mentions.add(canonical_prov)

                types.append(Entry(prov, NER_MAP[row.ner], row.gloss, None, None))
                types.append(Entry(canonical_prov, NER_MAP[row.ner], row.canonical_gloss, None, None))
                # a canonical mention line
                cmentions.append(Entry(prov, "canonical_mention", canonical_prov, None, None))
                cmentions.append(Entry(canonical_prov, "canonical_mention", canonical_prov, None, None))
                # a link line (only for canonical mention
                links.append(Entry(canonical_prov, "link", row.best_entity, None, row.best_entity_score))
            logger.info("Wrote %d mentions", len(valid_mentions))

            cur.execute("""
        SELECT subject_span, relation, object_span, s.doc_id, s.doc_char_begin[1], s.doc_char_end[public.array_length(s.doc_char_end)], confidence
        FROM _relation r, {sentence} s
        WHERE r.doc_id = s.doc_id aND r.sentence_id = s.id
        ORDER BY subject_span, relation, object_span
        """.format(sentence=sentence_table))
            logger.info("Found %d rows", cur.rowcount)

            for row in cur:
                if "_ENG_" not in row.doc_id or row.relation not in ALL_RELATIONS: continue
                subject_prov = MFile.to_prov(row.subject_span)
                object_prov = MFile.to_prov(row.object_span)
                if subject_prov not in valid_mentions or object_prov not in valid_mentions:
                    logger.warning("Ignoring for invalid mention: %s", row)
                    continue

                relations.append(Entry(subject_prov, row.relation, object_prov, MFile.to_prov([row.doc_id, row.doc_char_begin, row.doc_char_end]), row.confidence))
    writer = csv.writer(args.output, delimiter="\t")
    for row in sorted(set(types)):
        writer.writerow(row)
    for row in sorted(set(cmentions)):
        writer.writerow(row)
    for row in sorted(set(links)):
        writer.writerow(row)
    for row in sorted(set(relations)):
        writer.writerow(row)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Export data from the database')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('submission', help='Export a submission as an m-file')
    command_parser.add_argument('-i', '--submission_id', type=int, required=True, help="Submission id to export")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="File to export to")
    command_parser.set_defaults(func=do_submission)

    command_parser = subparsers.add_parser('stanford', help='Export output from a Stanford table.')
    command_parser.add_argument('-k', '--kb-table', type=str, default="public.kb_patterns_2016_8_28_16", help="KB table")
    command_parser.add_argument('-m', '--mention-table', type=str, default="public.mention_8_30_16", help="Mention table to use")
    command_parser.add_argument('-s', '--sentence-table', type=str, default="public.sentence_8_30_16", help="Sentence table")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="File to export to")
    command_parser.set_defaults(func=do_stanford)


    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

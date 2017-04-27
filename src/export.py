#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export data from the database.
"""

import csv
import sys
import logging

from tqdm import tqdm

from kbpo import db
from kbpo.entry import MFile, Entry
from kbpo.defs import TYPES,NER_MAP,ALL_RELATIONS
import re

logger = logging.getLogger('kbpo')
logging.basicConfig(level=logging.INFO)


regex = re.compile('[^\w]')

def entity_name(link_name, entity_hash):
    link_name_ = regex.sub('', link_name)
    return ':'+'_'.join([link_name_, entity_hash[:10]])

def do_submission_to_kb(args):
    writer = csv.writer(args.output, delimiter="\t",  quoting=csv.QUOTE_NONE, escapechar='', quotechar='')
    writer.writerow(["submission"+str(args.submission_id)])
    with db.CONN:
        with db.CONN.cursor() as cur:
            db.register_composite('kbpo.span', cur)
            cur.execute("""
                         SELECT md5(l.link_name)as entity_hash, wikify(l.link_name) as entity_wikiname,mode(m.mention_type) AS mention_type, mode(as_prov(c.mention_id)) AS canonical_prov, mode(c.gloss) as canonical_gloss, max(confidence) AS confidence 
                          FROM submission_mention AS m 
                          JOIN submission_mention AS c ON m.canonical_id = c.mention_id 
                          JOIN submission_link AS l ON c.mention_id = l.mention_id 
                          WHERE m.submission_id = 1 AND c.submission_id = 1 AND l.submission_id = 1 AND m.mention_type != 'DATE'
                          GROUP BY l.link_name, (m.mention_id).doc_id ORDER BY l.link_name;
            """, [args.submission_id]*3)
            entity_ids = set()
            for row in cur:
                
                if row.mention_type in TYPES:
                    type_ = row.mention_type
                elif row.mention_type in NER_MAP:
                    type_ = NER_MAP[row.mention_type]
                else:
                    logger.debug("skipping %s for invalid type", row)
                    continue
                if not row.entity_hash in entity_ids:
                    writer.writerow([entity_name(row.entity_wikiname, row.entity_hash), 'type', type_, None, None])
                    entity_ids.add(row.entity_hash)
                writer.writerow([entity_name(row.entity_wikiname, row.entity_hash), 'canonical_mention', "\""+row.canonical_gloss+"\"", row.canonical_prov, row.confidence])

            #All mentions
            cur.execute("""SELECT md5(l.link_name) as link_hash, 
                      wikify(l.link_name) as link_name, 
                      m.mention_id, 
                      m.gloss, 
                      l.confidence
               FROM submission_mention as m 
               JOIN submission_link as l ON m.canonical_id = l.mention_id 
               WHERE m.submission_id = %s AND l.submission_id = %s AND m.mention_type != 'DATE';
            """, [args.submission_id]*2)
            for row in cur:
                writer.writerow([entity_name(row.link_name, row.link_hash), 'mention', "\""+row.gloss+"\"", MFile.to_prov(row.mention_id), row.confidence])
            #All relations
            cur.execute("""
            SELECT 
            DISTINCT ON (subject_hash, r.relation, object_hash)
            md5(sl.link_name) AS subject_hash,
            wikify(sl.link_name) AS subject_link_name,
            s.mention_type AS subject_type,
            r.relation, 
            md5(ol.link_name) AS object_hash,
            wikify(ol.link_name) AS object_link_name,
            o.mention_type AS object_type,
            o.gloss AS object_gloss,
            o.mention_id AS object_id,
            r.confidence,
            r.provenances
            FROM submission_relation AS r 
            LEFT JOIN submission_mention AS s ON r.subject_id = s.mention_id 
            LEFT JOIN submission_link AS sl ON s.canonical_id = sl.mention_id 
            LEFT JOIN submission_mention AS o ON r.object_id = o.mention_id 
            LEFT JOIN submission_link AS ol ON o.canonical_id = ol.mention_id 
            WHERE r.submission_id = %s AND s.submission_id = %s AND o.submission_id = %s AND sl.submission_id = %s AND ol.submission_id = %s
            ORDER BY
            subject_hash, r.relation, object_hash,
            LEAST(abs(2 - abs((o.mention_id).char_begin - (s.mention_id).char_end)::INTEGER), 
                abs(2 - abs((s.mention_id).char_begin - (o.mention_id).char_end)::INTEGER)),
            r.confidence;
            """, [args.submission_id]*5)
            for row in cur:
                assert row.subject_type in set(['PER', 'ORG', 'GPE']), 'Subject type: '+str(row.subject_type)+' not one of PER, ORG, GPE'
                if row.object_type == 'TITLE':
                    writer.writerow([entity_name(row.subject_link_name, row.subject_hash), row.relation, "\""+row.object_gloss+"\"", ','.join([MFile.to_prov(row.object_id)]+ row.provenances),  row.confidence])
                elif row.object_type == 'DATE':
                    writer.writerow([entity_name(row.subject_link_name, row.subject_hash), row.relation, "\""+row.object_link_name+"\"",','.join([MFile.to_prov(row.object_id)]+ row.provenances), row.confidence])
                else:
                    writer.writerow([entity_name(row.subject_link_name, row.subject_hash), row.relation, entity_name(row.object_link_name, row.object_hash),','.join([MFile.to_prov(row.object_id)]+ row.provenances), row.confidence])

def do_submission(args):
    writer = csv.writer(args.output, delimiter="\t")
    with db.CONN:
        with db.CONN.cursor() as cur:
            mention_ids = set([])
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
            # Get every single mention from the database.
            cur.execute("""
            SELECT DISTINCT ON (m.doc_id, m.doc_char_begin, m.doc_char_end)
            m.doc_id, m.doc_char_begin, m.doc_char_end, m.gloss, 
            n.ner, m.best_entity, m.best_entity_score,
            n.doc_canonical_char_begin, n.doc_canonical_char_end, n.gloss AS canonical_gloss
            FROM {mention} m, {mention} n
            WHERE m.doc_id = n.doc_id
              AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end
              AND m.doc_id ~ 'ENG_' AND m.doc_id !~ '_DF_'
              AND m.ner = n.ner
              AND m.parent_id IS NULL and n.parent_id IS NULL
              AND m.corpus_id = 2016
              AND is_kbpo_type(n.ner)
            """.format(mention=mention_table))

            valid_mentions = set([])
            for row in tqdm(cur, total=cur.rowcount, desc="Getting mentions"):
                if "ENG_" not in row.doc_id: continue
                if "ENG_DF" in row.doc_id: continue
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
            logger.info("Found %d mentions", len(valid_mentions))

            cur.execute("""
            WITH _relation AS (
            SELECT m.doc_id AS doc_id, m.sentence_id, m.id AS subject_id, (m.doc_id, m.doc_char_begin, m.doc_char_end)::SPAN AS subject_span,
                   relation,
                   n.id AS object_id, (n.doc_id, n.doc_char_begin, n.doc_char_end)::SPAN AS object_span,
                   confidence
            FROM {mention} m, {mention} n, {kb} k
            WHERE
                m.doc_id = n.doc_id AND m.sentence_id = n.sentence_id AND m.id = k.subject_id AND n.id = k.object_id
                AND m.corpus_id = 2016
                AND m.parent_id IS NULL and n.parent_id IS NULL
                AND is_kbpo_reln(relation)
            )
        SELECT subject_span, relation, object_span, s.doc_id, s.doc_char_begin[1], s.doc_char_end[public.array_length(s.doc_char_end)], confidence
        FROM _relation r, {sentence} s
        WHERE r.doc_id = s.doc_id AND r.sentence_id = s.id
        ORDER BY subject_span, relation, object_span
        """.format(kb=kb_table,mention=mention_table,sentence=sentence_table))

            for row in tqdm(cur, total=cur.rowcount, desc="Getting relations"):
                if "ENG_" not in row.doc_id or row.relation not in ALL_RELATIONS: continue
                if "ENG_DF" in row.doc_id: continue
                if row.relation not in ALL_RELATIONS: continue
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

    command_parser = subparsers.add_parser('submission2kb', help='Export a submission as a kb')
    command_parser.add_argument('-i', '--submission_id', type=int, required=True, help="Submission id to export")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="File to export to")
    command_parser.set_defaults(func=do_submission_to_kb)

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

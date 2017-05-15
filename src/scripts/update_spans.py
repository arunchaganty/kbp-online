#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Converts sentence.doc_char_begin, sentence.doc_char_end to sentence.tokens.
"""
import sys
from tqdm import tqdm
from collections import namedtuple
from kbpo import db

def do_command(_):
    with db.CONN:
        with db.CONN.cursor() as cur:
            # Create temporary table to replace sentence.
            cur.execute("""DROP TABLE IF EXISTS _sentence;""")
            cur.execute("""
                CREATE TABLE _sentence (
                  id INTEGER NOT NULL DEFAULT nextval('sentence_id_seq'),
                  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

                  doc_id TEXT NOT NULL,
                  span INT4RANGE NOT NULL,
                  sentence_index SMALLINT NOT NULL,

                  gloss TEXT NOT NULL,

                  token_spans INT4RANGE[] NOT NULL,
                  words TEXT[] NOT NULL,
                  lemmas TEXT[] NOT NULL,
                  pos_tags TEXT[] NOT NULL,
                  ner_tags TEXT[] NOT NULL,
                  dependencies TEXT NOT NULL
                );""")
            NewRow = namedtuple("NewRow", "id updated doc_id span sentence_index gloss tokens words lemmas pos_tags ner_tags dependencies".split())

            values = []
            cur.execute("""SELECT * FROM sentence""")
            for row in tqdm(cur, total=cur.rowcount):
                begin, end = row.doc_char_begin, row.doc_char_end
                tokens = [db.Int4NumericRange(int(b), int(e)) for b, e in zip(begin, end)]
                row_ = NewRow(row.id, row.updated, row.doc_id, row.span, row.sentence_index, row.gloss, tokens, row.words, row.lemmas, row.pos_tags, row.ner_tags, row.dependencies)
                values.append(row_)
            db.execute_values(cur, """INSERT INTO _sentence(id, updated, doc_id, span, sentence_index, gloss, token_span, words, lemmas, pos_tags, ner_tags, dependencies) VALUES %s""", values)

            # ADD constraints
            cur.execute("""
                ALTER TABLE _sentence ADD CONSTRAINT _sentence_pkey PRIMARY KEY (doc_id, span);
                ALTER TABLE _sentence ADD CONSTRAINT _sentence_doc_id_fkey FOREIGN KEY (doc_id) REFERENCES document(id);
                ALTER TABLE _sentence ADD CONSTRAINT __word_length_same_as_tokens_length CHECK ((array_lower(words, 1) = array_lower(token_spans, 1)));
                ALTER TABLE _sentence ADD CONSTRAINT __word_length_same_as_lemma_length CHECK ((array_lower(words, 1) = array_lower(lemmas, 1)));
                ALTER TABLE _sentence ADD CONSTRAINT __word_length_same_as_ner_length CHECK ((array_lower(words, 1) = array_lower(ner_tags, 1)));
                ALTER TABLE _sentence ADD CONSTRAINT __word_length_same_as_pos_length CHECK ((array_lower(words, 1) = array_lower(pos_tags, 1)));
                ALTER TABLE _sentence ADD CONSTRAINT _word_length_same_as_tokens_length CHECK ((array_upper(words, 1) = array_upper(token_spans, 1)));
                ALTER TABLE _sentence ADD CONSTRAINT _word_length_same_as_lemma_length CHECK ((array_upper(words, 1) = array_upper(lemmas, 1)));
                ALTER TABLE _sentence ADD CONSTRAINT _word_length_same_as_ner_length CHECK ((array_upper(words, 1) = array_upper(ner_tags, 1)));
                ALTER TABLE _sentence ADD CONSTRAINT _word_length_same_as_pos_length CHECK ((array_upper(words, 1) = array_upper(pos_tags, 1)));
                """)
            cur.execute("""DROP TABLE sentence;""")
            cur.execute("""ALTER TABLE _sentence RENAME TO sentence;""")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Converts sentence.doc_char_begin, sentence.doc_char_end to sentence.tokens.')
    parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)

--
-- Basic tables that describe the task. 
--
SET search_path TO kbpo;

BEGIN TRANSACTION;
-- document
CREATE TABLE document (
  id TEXT PRIMARY KEY,
  -- When the document was added to the database
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
  title TEXT, -- Document title
  doc_date DATE, -- Document date
  doc_length INTEGER, -- Document length (useful for consistency)
  doc_digest TEXT, -- an MD5 hash of the document.
  gloss TEXT -- Raw document text
) DISTRIBUTED BY (id);
COMMENT ON TABLE document IS 'Original documents, dates, titles';

-- sentence
CREATE SEQUENCE sentence_id_seq;
CREATE TABLE sentence (
  id INTEGER DEFAULT nextval('sentence_id_seq'),
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  doc_id TEXT NOT NULL REFERENCES document(id), -- Reference to document
  sentence_index SMALLINT,

  words TEXT[] NOT NULL,
  lemmas TEXT[] NOT NULL,
  pos_tags TEXT[] NOT NULL,
  ner_tags TEXT[] NOT NULL,
  doc_char_begin INTEGER[] NOT NULL,
  doc_char_end INTEGER[] NOT NULL,
  gloss TEXT,
  dependencies TEXT NOT NULL,

  CONSTRAINT _word_length_same_as_doc_char_begin_length CHECK ((array_lower(words, 1) = array_lower(doc_char_begin, 1))),
  CONSTRAINT _word_length_same_as_doc_char_end_length CHECK ((array_lower(words, 1) = array_lower(doc_char_end, 1))),
  CONSTRAINT _word_length_same_as_lemma_length CHECK ((array_lower(words, 1) = array_lower(lemmas, 1))),
  CONSTRAINT _word_length_same_as_ner_length CHECK ((array_lower(words, 1) = array_lower(ner_tags, 1))),
  CONSTRAINT _word_length_same_as_pos_length CHECK ((array_lower(words, 1) = array_lower(pos_tags, 1))),
  CONSTRAINT word_length_same_as_doc_char_begin_length CHECK ((array_upper(words, 1) = array_upper(doc_char_begin, 1))),
  CONSTRAINT word_length_same_as_doc_char_end_length CHECK ((array_upper(words, 1) = array_upper(doc_char_end, 1))),
  CONSTRAINT word_length_same_as_lemma_length CHECK ((array_upper(words, 1) = array_upper(lemmas, 1))),
  CONSTRAINT word_length_same_as_ner_length CHECK ((array_upper(words, 1) = array_upper(ner_tags, 1))),
  CONSTRAINT word_length_same_as_pos_length CHECK ((array_upper(words, 1) = array_upper(pos_tags, 1))),
  PRIMARY KEY (doc_id, sentence_index)
) DISTRIBUTED BY (doc_id);
COMMENT ON TABLE sentence IS 'Sentences and features, from Stanford CoreNLP';
CREATE INDEX sentence_id_idx ON sentence(id);

-- mention
CREATE TABLE suggested_mention (
  id SPAN NOT NULL,
  doc_id TEXT NOT NULL REFERENCES document,
  updated TIMESTAMP NOT NULL,

  sentence_id INTEGER NOT NULL,

  mention_type TEXT NOT NULL,
  canonical_span SPAN NOT NULL,
  gloss TEXT NOT NULL,
  CONSTRAINT doc_id_matches CHECK ((id).doc_id = doc_id),
  CONSTRAINT char_spans_exclusive CHECK ((id).char_end > (id).char_begin),
  CONSTRAINT canonical_char_spans_exclusive CHECK ((canonical_span).char_end > (canonical_span).char_begin),
  PRIMARY KEY(doc_id, id)
) DISTRIBUTED BY (doc_id);
COMMENT ON TABLE suggested_mention IS 'Entity mentions extracted by Stanford CoreNLP';
CREATE INDEX suggested_mention_id_idx ON suggested_mention(id);

-- link
CREATE TABLE suggested_link (
  id SPAN,
  doc_id TEXT,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,

  CONSTRAINT doc_id_matches CHECK ((id).doc_id = doc_id),
  CONSTRAINT char_spans_exclusive CHECK ((id).char_end > (id).char_begin),
  CONSTRAINT mention_exists FOREIGN KEY (doc_id, id) REFERENCES suggested_mention,
  PRIMARY KEY(doc_id, id)
) DISTRIBUTED BY (doc_id);
COMMENT ON TABLE suggested_link IS 'Entity links suggested by Stanford CoreNLP';
CREATE INDEX suggested_link_id_idx ON suggested_link(id);

COMMIT;

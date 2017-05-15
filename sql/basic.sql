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
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE document IS 'Original documents, dates, titles';

-- document tags (to just help us)
CREATE TABLE document_tag (
  doc_id TEXT REFERENCES document,
  tag TEXT,
  UNIQUE (doc_id, tag)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE document_tag IS 'Tags for documents';
CREATE INDEX document_tag_doc_id_idx ON document_tag(doc_id);

-- sentence
CREATE SEQUENCE sentence_id_seq;
CREATE TABLE sentence (
  id INTEGER NOT NULL DEFAULT nextval('sentence_id_seq'),
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  doc_id TEXT NOT NULL REFERENCES document(id), -- Reference to document
  span INT4RANGE NOT NULL,
  sentence_index SMALLINT NOT NULL,

  token_spans INT4RANGE[] NOT NULL,
  words TEXT[] NOT NULL,
  lemmas TEXT[] NOT NULL,
  pos_tags TEXT[] NOT NULL,
  ner_tags TEXT[] NOT NULL,
  gloss TEXT NOT NULL,
  dependencies TEXT NOT NULL,

  CONSTRAINT _word_length_same_as_tokens_length CHECK ((array_lower(words, 1) = array_lower(token_spans, 1))),
  CONSTRAINT _word_length_same_as_lemma_length CHECK ((array_lower(words, 1) = array_lower(lemmas, 1))),
  CONSTRAINT _word_length_same_as_ner_length CHECK ((array_lower(words, 1) = array_lower(ner_tags, 1))),
  CONSTRAINT _word_length_same_as_pos_length CHECK ((array_lower(words, 1) = array_lower(pos_tags, 1))),
  CONSTRAINT word_length_same_as_tokens_length CHECK ((array_upper(words, 1) = array_upper(token_spans, 1))),
  CONSTRAINT word_length_same_as_lemma_length CHECK ((array_upper(words, 1) = array_upper(lemmas, 1))),
  CONSTRAINT word_length_same_as_ner_length CHECK ((array_upper(words, 1) = array_upper(ner_tags, 1))),
  CONSTRAINT word_length_same_as_pos_length CHECK ((array_upper(words, 1) = array_upper(pos_tags, 1))),
  PRIMARY KEY (doc_id, span)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE sentence IS 'Sentences and features, from Stanford CoreNLP';
CREATE INDEX sentence_id_idx ON sentence(id);

-- mention
CREATE TABLE suggested_mention (
  doc_id TEXT NOT NULL REFERENCES document,
  span INT4RANGE NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  sentence_id INTEGER,

  mention_type TEXT NOT NULL,
  canonical_span INT4RANGE NOT NULL,
  gloss TEXT NOT NULL,

  PRIMARY KEY(doc_id, span)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE suggested_mention IS 'Entity mentions extracted by Stanford CoreNLP';

-- link
CREATE TABLE suggested_link (
  doc_id TEXT,
  span INT4RANGE NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,

  CONSTRAINT mention_exists FOREIGN KEY (doc_id, span) REFERENCES suggested_mention,
  PRIMARY KEY(doc_id, span)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE suggested_link IS 'Entity links suggested by Stanford CoreNLP';

COMMIT;

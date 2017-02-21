--
-- Database schemata for KBP online
--

-- document
CREATE TABLE IF NOT EXISTS document (
  doc_id TEXT PRIMARY KEY,
  updated TIMESTAMP NOT NULL, -- When the document was added to the database
  title TEXT, -- Document title
  doc_date DATE, -- Document date
  doc_length INTEGER, -- Document length (useful for consistency)
  gloss TEXT -- Raw document text
) DISTRIBUTED BY doc_id;
COMMENT ON document 'Table containing original documents, dates, titles';

-- sentence
CREATE SEQUENCE sentence_id_seq;
CREATE TABLE IF NOT EXISTS sentence (
  id INTEGER PRIMARY KEY DEFAULT nextval(sentence_id_seq),
  updated TIMESTAMP NOT NULL, -- When this sentence was added to the database.
  doc_id TEXT NOT NULL REFERENCES (document), -- Reference to document
  sentence_index SMALLINT, -- 
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
  UNIQUE (doc_id, sentence_index)
) DISTRIBUTED BY doc_id;
COMMENT ON sentence 'Table containing sentences within a document, as specified by CoreNLP';

-- mention
CREATE SEQUENCE mention_id_seq;
CREATE TABLE IF NOT EXISTS mention (
  id INTEGER DEFAULT nextval(mention_id_seq),
  doc_id TEXT NOT NULL REFERENCES (document),
  doc_char_begin INTEGER NOT NULL,
  doc_char_end INTEGER NOT NULL,
  updated TIMESTAMP NOT NULL,

  doc_canonical_char_begin INTEGER NOT NULL,
  doc_canonical_char_end INTEGER NOT NULL,
  sentence_id INTEGER NOT NULL,
  ner TEXT NOT NULL,
  gloss TEXT,
  PRIMARY KEY (doc_id, doc_char_begin, doc_char_end),
  CONSTRAINT char_spans_exclusive CHECK ((doc_char_end > doc_char_begin)),
  CONSTRAINT char_spans_valid CHECK ((doc_char_end >= doc_char_begin))
  CONSTRAINT canonical_char_spans_exclusive CHECK ((doc_canonical_char_end > doc_canonical_char_begin)),
  CONSTRAINT canonical_char_spans_valid CHECK ((doc_canonical_char_end >= doc_canonical_char_begin))
) DISTRIBUTED BY doc_id;
COMMENT ON mention 'Table containing mentions within a document, as specified by CoreNLP';


-- link
CREATE TABLE IF NOT EXISTS entity_link (
  id INTEGER PRIMARY KEY,
  doc_id TEXT NOT NULL,
  doc_char_begin INTEGER NOT NULL,
  doc_char_end INTEGER NOT NULL,
  updated TIMESTAMP NOT NULL,

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,
  PRIMARY KEY (doc_id, doc_char_begin, doc_char_end),
  CONSTRAINT char_spans_exclusive CHECK ((doc_char_end > doc_char_begin)),
  CONSTRAINT char_spans_valid CHECK ((doc_char_end >= doc_char_begin)),
) DISTRIBUTED BY doc_id;

-- submission_mention
CREATE SEQUENCE submission_mention_id_seq;
CREATE TABLE IF NOT EXISTS submission_mention (
  id INTEGER DEFAULT nextval(submission_mention_id_seq),
  system_id INTEGER NOT NULL,
  doc_id TEXT NOT NULL REFERENCES (document),
  doc_char_begin INTEGER NOT NULL,
  doc_char_end INTEGER NOT NULL,
  updated TIMESTAMP NOT NULL,

  doc_canonical_char_begin INTEGER NOT NULL,
  doc_canonical_char_end INTEGER NOT NULL,
  ner TEXT NOT NULL,
  gloss TEXT,
  CONSTRAINT char_spans_exclusive CHECK ((doc_char_end > doc_char_begin)),
  CONSTRAINT char_spans_valid CHECK ((doc_char_end >= doc_char_begin)),
  CONSTRAINT canonical_char_spans_exclusive CHECK ((doc_canonical_char_end > doc_canonical_char_begin)),
  CONSTRAINT canonical_char_spans_valid CHECK ((doc_canonical_char_end >= doc_canonical_char_begin))
  PRIMARY KEY (system_id, doc_id, doc_char_begin, doc_char_end)
) DISTRIBUTED BY doc_id;
COMMENT ON submission_mention 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX ON submission_mention(doc_id);
CREATE INDEX ON submission_mention(doc_id, doc_char_begin, doc_char_end);

-- submission_link
CREATE SEQUENCE submission_link_id_seq;
CREATE TABLE IF NOT EXISTS submission_link (
  id INTEGER DEFAULT nextval(submission_link_id_seq),
  system_id INTEGER NOT NULL,
  doc_id TEXT NOT NULL REFERENCES (document),
  doc_char_begin INTEGER NOT NULL,
  doc_char_end INTEGER NOT NULL,
  updated TIMESTAMP NOT NULL,

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,
  CONSTRAINT char_spans_exclusive CHECK ((doc_char_end > doc_char_begin)),
  CONSTRAINT char_spans_valid CHECK ((doc_char_end >= doc_char_begin)),
  PRIMARY KEY (system_id, doc_id, doc_char_begin, doc_char_end)
) DISTRIBUTED BY doc_id;
COMMENT ON submission_link 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX ON submission_link(doc_id);
CREATE INDEX ON submission_link(doc_id, doc_char_begin, doc_char_end);

-- submission_relation
CREATE SEQUENCE submission_relation_id_seq;
CREATE TABLE IF NOT EXISTS submission_relation (
  id INTEGER DEFAULT nextval(submission_relation_id_seq),
  system_id INTEGER NOT NULL,
  doc_id TEXT NOT NULL REFERENCES (document),
  subject_char_begin INTEGER NOT NULL,
  subject_char_end INTEGER NOT NULL,
  relation TEXT NOT NULL,
  object_char_begin INTEGER NOT NULL,
  object_char_end INTEGER NOT NULL,
  updated TIMESTAMP NOT NULL,

  subject_gloss TEXT,
  object_gloss TEXT,
  confidence REAL DEFAULT 1.0,
  CONSTRAINT char_spans_exclusive CHECK ((doc_char_end > doc_char_begin)),
  CONSTRAINT char_spans_valid CHECK ((doc_char_end >= doc_char_begin)),
  PRIMARY KEY (system_id, doc_id, subject_char_begin, subject_char_end, object_char_begin, object_char_end)
) DISTRIBUTED BY doc_id;
COMMENT ON submission_relation 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX ON submission_relation(doc_id);
CREATE INDEX ON submission_relation(doc_id, subject_char_begin, subject_char_end, object_char_begin, object_char_end);

-- submission_kb
-- TODO
-- submission_score
-- TODO

-- evaluation_mention
-- evaluation_link
-- evaluation_relation
-- evaluation_mention_turk
-- evaluation_link_turk
-- evaluation_relation_turk
-- mturk_assignment

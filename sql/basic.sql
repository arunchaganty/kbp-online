--
-- Basic tables that describe the task. 
--

-- document
CREATE TABLE IF NOT EXISTS document (
  id TEXT PRIMARY KEY,
  -- When the document was added to the database
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
  title TEXT, -- Document title
  doc_date DATE, -- Document date
  doc_length INTEGER, -- Document length (useful for consistency)
  doc_digest TEXT UNIQUE, -- an MD5 hash of the document.
  gloss TEXT -- Raw document text
) DISTRIBUTED BY id;
COMMENT ON document 'Original documents, dates, titles';

-- sentence
CREATE SEQUENCE sentence_id_seq;
CREATE TABLE IF NOT EXISTS sentence (
  id INTEGER PRIMARY KEY DEFAULT nextval(sentence_id_seq),
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  doc_id TEXT NOT NULL REFERENCES (document), -- Reference to document
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
  UNIQUE (doc_id, sentence_index)
) DISTRIBUTED BY doc_id;
COMMENT ON sentence 'Sentences and features, from Stanford CoreNLP';

-- mention
CREATE TABLE IF NOT EXISTS suggested_mention (
  id SPAN PRIMARY KEY,
  updated TIMESTAMP NOT NULL,

  sentence_id INTEGER NOT NULL,

  mention_type TEXT NOT NULL,
  canonical_span SPAN NOT NULL,
  gloss TEXT NOT NULL,
  CONSTRAINT char_spans_exclusive CHECK ((id.char_end > id.char_begin)),
  CONSTRAINT canonical_char_spans_exclusive CHECK ((canonical_span.char_end > canonical_span.char_begin)),
  CONSTRAINT doc_exists FOREIGN KEY id.doc_id REFERENCES document(id)
) DISTRIBUTED BY doc_id;
COMMENT ON suggested_mention 'Entity mentions extracted by Stanford CoreNLP';

-- link
CREATE TABLE IF NOT EXISTS suggested_link (
  id SPAN PRIMARY KEY,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,

  CONSTRAINT char_spans_exclusive CHECK ((id.char_end > id.char_begin)),
  CONSTRAINT mention_exists FOREIGN KEY id REFERENCES mention(id)
) DISTRIBUTED BY doc_id;
COMMENT ON suggested_link 'Entity links suggested by Stanford CoreNLP';


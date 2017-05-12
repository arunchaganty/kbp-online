--
SET search_path TO kbpo;

BEGIN TRANSACTION;

CREATE SEQUENCE submission_id_seq;
CREATE TABLE  submission (
    id INTEGER PRIMARY KEY DEFAULT nextval('submission_id_seq'),
    updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

    name TEXT NOT NULL, -- short textual identifier for this submission.
    corpus_tag TEXT NOT NULL,
    details TEXT -- A more detailed description of the submission.
); -- DISTRIBUTED BY (id);    
COMMENT ON TABLE submission IS 'Summary of a submission';

-- submission_mention
CREATE TABLE  submission_mention (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  span INT4RANGE NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  canonical_span INT4RANGE NOT NULL,
  mention_type TEXT NOT NULL,
  gloss TEXT,

  PRIMARY KEY (submission_id, doc_id, span),
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE submission_mention IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX submission_mention_doc_idx ON submission_mention(doc_id, span);

-- submission_link
CREATE TABLE  submission_link (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  span INT4RANGE NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,

  PRIMARY KEY (submission_id, doc_id, span),
  CONSTRAINT mention_exists FOREIGN KEY (submission_id, doc_id, span) REFERENCES submission_mention
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE submission_link IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX submission_link_doc_idx ON submission_link(doc_id, span);

-- submission_relation
CREATE TABLE  submission_relation (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  subject INT4RANGE NOT NULL,
  object INT4RANGE NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  relation TEXT NOT NULL,
  provenances SPAN[] NOT NULL,
  confidence REAL DEFAULT 1.0,
  PRIMARY KEY (submission_id, doc_id, subject, object),
  CONSTRAINT subject_exists FOREIGN KEY (submission_id, doc_id, subject) REFERENCES submission_mention,
  CONSTRAINT object_exists FOREIGN KEY (submission_id, doc_id, object) REFERENCES submission_mention
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE submission_relation IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX submission_relation_subject_idx ON submission_relation(doc_id, subject);
CREATE INDEX submission_relation_object_idx ON submission_relation(doc_id, object);

-- submission_score 
CREATE TABLE  submission_score (
  submission_id INTEGER NOT NULL REFERENCES submission,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
  score_type TEXT NOT NULL,
  score SCORE,
  PRIMARY KEY (submission_id, score_type)
); -- DISTRIBUTED BY (submission_id);
COMMENT ON TABLE submission_score IS 'Summary of scores for a system.';
CREATE INDEX submission_score_submission_idx ON submission_score(submission_id);

COMMIT;

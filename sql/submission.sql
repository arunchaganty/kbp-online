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
    -- NOTE: add a user_id field in the future.
) DISTRIBUTED BY (id);    
COMMENT ON TABLE submission IS 'Summary of a submission';

-- submission_mention
CREATE TABLE  submission_mention (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  mention_id SPAN NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  canonical_id SPAN NOT NULL,
  mention_type TEXT NOT NULL,
  gloss TEXT,

  PRIMARY KEY (doc_id, submission_id, mention_id),
  CONSTRAINT valid_span CHECK (span_is_valid(mention_id)),
  CONSTRAINT valid_canonical_span CHECK (span_is_valid(canonical_id)),
  CONSTRAINT doc_agrees CHECK((mention_id).doc_id = doc_id),
  CONSTRAINT canonical_doc_agrees CHECK((canonical_id).doc_id = doc_id)
) DISTRIBUTED BY (doc_id);
COMMENT ON TABLE submission_mention IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX submission_mention_mention_idx ON submission_mention(mention_id);
CREATE INDEX submission_mention_doc_idx ON submission_mention(doc_id);

-- submission_link
CREATE TABLE  submission_link (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  mention_id SPAN NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,

  PRIMARY KEY (doc_id, submission_id, mention_id),
  CONSTRAINT doc_agrees CHECK((mention_id).doc_id = doc_id),
  CONSTRAINT mention_exists FOREIGN KEY (doc_id, submission_id, mention_id) REFERENCES submission_mention
) DISTRIBUTED BY (doc_id);
COMMENT ON TABLE submission_link IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX submission_link_doc_idx ON submission_link(doc_id);
CREATE INDEX submission_link_mention_idx ON submission_link(mention_id);

-- submission_relation
CREATE TABLE  submission_relation (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  subject_id SPAN NOT NULL,
  object_id SPAN NOT NULL,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  relation TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,
  PRIMARY KEY (doc_id, submission_id, subject_id, object_id),
  CONSTRAINT subject_doc_agrees CHECK((subject_id).doc_id = doc_id),
  CONSTRAINT object_doc_agrees CHECK((object_id).doc_id = doc_id),
  CONSTRAINT subject_exists FOREIGN KEY (doc_id, submission_id, subject_id) REFERENCES submission_mention,
  CONSTRAINT object_exists FOREIGN KEY (doc_id, submission_id, object_id) REFERENCES submission_mention
) DISTRIBUTED BY (doc_id);
COMMENT ON TABLE submission_relation IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX submission_relation_doc_idx ON submission_relation(doc_id);
CREATE INDEX submission_relation_subject_idx ON submission_relation(subject_id);
CREATE INDEX submission_relation_object_idx ON submission_relation(object_id);
CREATE INDEX submission_relation_relation_idx ON submission_relation(subject_id, object_id);

-- submission_score 
CREATE TABLE  submission_score (
  submission_id INTEGER NOT NULL REFERENCES submission,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
  score_type TEXT NOT NULL,
  score SCORE,
  PRIMARY KEY (submission_id, score_type)
) DISTRIBUTED BY (submission_id);
COMMENT ON TABLE submission_score IS 'Summary of scores for a system.';
CREATE INDEX submission_score_submission_idx ON submission_score(submission_id);

COMMIT;

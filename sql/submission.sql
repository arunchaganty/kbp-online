--
-- Submission schema
--
BEGIN;

CREATE SEQUENCE submission_id_seq;
CREATE TABLE IF NOT EXISTS submission (
    id INTEGER PRIMARY KEY DEFAULT nextval('submission_id_seq'),
    updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

    name TEXT NOT NULL, -- short textual identifier for this submission.
    details TEXT -- A more detailed description of the submission.
    -- NOTE: add a user_id field in the future.
);    
COMMENT ON TABLE submission IS 'Summary of a submission';

-- submission_mention
CREATE TABLE IF NOT EXISTS submission_mention (
  submission_id INTEGER NOT NULL REFERENCES submission,
  doc_id TEXT NOT NULL REFERENCES document,
  mention_id SPAN NOT NULL,
  updated TIMESTAMP NOT NULL,

  canonical_id SPAN NOT NULL,
  mention_type TEXT NOT NULL,
  gloss TEXT,

  PRIMARY KEY (submission_id, mention_id),
  CONSTRAINT valid_span CHECK (span_is_valid(mention_id)),
  CONSTRAINT valid_canonical_span CHECK (span_is_valid(canonical_id)),
  CONSTRAINT doc_agrees CHECK((mention_id).doc_id = doc_id),
  CONSTRAINT canonical_doc_agrees CHECK((canonical_id).doc_id = doc_id)
); -- DISTRIBUTED BY doc_id;
COMMENT ON TABLE submission_mention IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX ON submission_mention(mention_id);
CREATE INDEX ON submission_mention(doc_id);

-- submission_link
CREATE TABLE IF NOT EXISTS submission_link (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  mention_id SPAN NOT NULL,
  updated TIMESTAMP NOT NULL,

  link_name TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,

  PRIMARY KEY (submission_id, mention_id),
  CONSTRAINT doc_agrees CHECK((mention_id).doc_id = doc_id),
  CONSTRAINT mention_exists FOREIGN KEY (submission_id, mention_id) REFERENCES submission_mention
); -- DISTRIBUTED BY doc_id;
COMMENT ON TABLE submission_link IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX ON submission_link(doc_id);
CREATE INDEX ON submission_link(mention_id);

-- submission_relation
CREATE TABLE IF NOT EXISTS submission_relation (
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document,
  subject_id SPAN NOT NULL,
  object_id SPAN NOT NULL,
  updated TIMESTAMP NOT NULL,

  relation TEXT NOT NULL,
  subject_gloss TEXT,
  object_gloss TEXT,
  confidence REAL DEFAULT 1.0,
  PRIMARY KEY (submission_id, subject_id, object_id),
  CONSTRAINT subject_doc_agrees CHECK((subject_id).doc_id = doc_id),
  CONSTRAINT object_doc_agrees CHECK((object_id).doc_id = doc_id),
  CONSTRAINT subject_exists FOREIGN KEY (submission_id, subject_id) REFERENCES submission_mention,
  CONSTRAINT object_exists FOREIGN KEY (submission_id, object_id) REFERENCES submission_mention
); -- DISTRIBUTED BY doc_id;
COMMENT ON TABLE submission_relation IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX ON submission_relation(doc_id);
CREATE INDEX ON submission_relation(subject_id);
CREATE INDEX ON submission_relation(object_id);
CREATE INDEX ON submission_relation(subject_id, object_id);

COMMIT;

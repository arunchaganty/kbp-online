--
SET search_path TO kbpo;

BEGIN TRANSACTION;

CREATE TYPE score AS (
  precision REAL,
  recall REAL,
  f1 REAL
);

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

  PRIMARY KEY (submission_id, doc_id, span)
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
  provenances INT4RANGE[] NOT NULL,
  confidence REAL DEFAULT 1.0,
  PRIMARY KEY (submission_id, doc_id, subject, object),
  CONSTRAINT subject_exists FOREIGN KEY (submission_id, doc_id, subject) REFERENCES submission_mention,
  CONSTRAINT object_exists FOREIGN KEY (submission_id, doc_id, object) REFERENCES submission_mention
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE submission_relation IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX submission_relation_subject_idx ON submission_relation(doc_id, subject);
CREATE INDEX submission_relation_object_idx ON submission_relation(doc_id, object);

-- submission_score 
CREATE SEQUENCE submission_score_id_seq;
CREATE TABLE  submission_score (
  id INTEGER PRIMARY KEY DEFAULT nextval('submission_score_id_seq'),
  submission_id INTEGER NOT NULL REFERENCES submission,
  updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
  score_type TEXT NOT NULL,
  score SCORE,
  left_interval SCORE,
  right_interval SCORE
); -- DISTRIBUTED BY (submission_id);
COMMENT ON TABLE submission_score IS 'Summary of scores for a system.';
CREATE INDEX submission_score_submission_idx ON submission_score(submission_id);

CREATE MATERIALIZED VIEW submission_entity_relation AS (
    SELECT s.submission_id,
           s.doc_id,
           s.subject,
           s.object,
           COALESCE(l.link_name, m.gloss) AS subject_entity,
           COALESCE(l_.link_name, n.gloss) AS object_entity,
           s.relation,
           s.provenances,
           s.confidence
        FROM submission_relation s
        JOIN submission_mention m ON (s.submission_id = m.submission_id AND s.doc_id = m.doc_id AND s.subject = m.span)
        LEFT OUTER JOIN submission_link l ON (s.submission_id = l.submission_id AND s.doc_id = l.doc_id AND m.canonical_span = l.span)
        JOIN submission_mention n ON (s.submission_id = n.submission_id AND s.doc_id = n.doc_id AND s.object = n.span)
        LEFT OUTER JOIN submission_link l_ ON (s.submission_id = l_.submission_id AND s.doc_id = l_.doc_id AND n.canonical_span = l_.span)
);

CREATE MATERIALIZED VIEW submission_statistics AS (
    SELECT s.submission_id, subject_entity, relation, COUNT(*) 
    FROM submission_entity_relation s
    GROUP BY s.submission_id, entity, relation
);

COMMIT;

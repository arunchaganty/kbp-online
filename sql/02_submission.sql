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
    details TEXT, -- A more detailed description of the submission.
    active BOOLEAN DEFAULT TRUE
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

DROP MATERIALIZED VIEW IF EXISTS submission_mention_link CASCADE;
CREATE MATERIALIZED VIEW submission_mention_link AS (
 SELECT 
    m.submission_id,
    m.doc_id,
    m.span,
    m.mention_type,
    m.gloss,
    n.span AS canonical_span,
    CASE
        WHEN n.mention_type = 'TITLE' THEN 'gloss:' || n.gloss
        WHEN n.mention_type = 'DATE' THEN 'date:' || n.gloss
        ELSE 'gloss:' || n.gloss
    END AS canonical_gloss,
    CASE
        WHEN n.mention_type = 'TITLE' THEN 'gloss:' || n.gloss
        WHEN n.mention_type = 'DATE' THEN COALESCE(l.link_name, 'date:' || n.gloss)
        ELSE COALESCE(l.link_name, 'gloss:' || n.gloss)
    END AS entity
   FROM submission_mention m
   JOIN submission_mention n ON (m.submission_id = n.submission_id AND m.doc_id = n.doc_id AND m.canonical_span = n.span)
   LEFT JOIN submission_link l ON (m.submission_id = l.submission_id AND m.doc_id = l.doc_id AND m.canonical_span = l.span)
);

DROP MATERIALIZED VIEW IF EXISTS submission_entity_relation CASCADE;
CREATE MATERIALIZED VIEW submission_entity_relation AS (
    SELECT s.submission_id,
           s.doc_id,
           s.subject,
           s.object,
           m.gloss AS subject_gloss,
           n.gloss AS object_gloss,
           m.canonical_span AS subject_canonical,
           n.canonical_span AS  object_canonical,
           m.canonical_gloss AS subject_canonical_gloss,
           n.canonical_gloss AS  object_canonical_gloss,
           m.mention_type AS subject_type,
           n.mention_type AS object_type,
           m.entity AS subject_entity,
           n.entity AS object_entity,
           s.relation,
           s.provenances,
           s.confidence
        FROM submission_relation s
        JOIN submission_mention_link m ON (s.submission_id = m.submission_id AND s.doc_id = m.doc_id AND s.subject = m.span)
        JOIN submission_mention_link n ON (s.submission_id = n.submission_id AND s.doc_id = n.doc_id AND s.object = n.span)
);

DROP MATERIALIZED VIEW IF EXISTS submission_statistics;
CREATE MATERIALIZED VIEW submission_statistics AS (
    SELECT s.submission_id, subject_entity, relation, COUNT(*) 
    FROM submission_entity_relation s
    GROUP BY s.submission_id, subject_entity, relation
);

DROP MATERIALIZED VIEW IF EXISTS submission_relation_counts;
CREATE MATERIALIZED VIEW submission_relation_counts AS (
    SELECT submission_id, relation, SUM(count) AS count
    FROM submission_statistics
    GROUP BY submission_id, relation
);

DROP MATERIALIZED VIEW IF EXISTS submission_entity_counts;
CREATE MATERIALIZED VIEW submission_entity_counts AS (
    SELECT submission_id, subject_entity, SUM(count) AS count
    FROM submission_statistics
    GROUP BY submission_id, subject_entity
);

DROP MATERIALIZED VIEW IF EXISTS submission_entity_relation_counts;
CREATE MATERIALIZED VIEW submission_entity_relation_counts AS (
    SELECT submission_id, subject_entity, COUNT(*)
    FROM submission_statistics
    GROUP BY submission_id, subject_entity
);

COMMIT;

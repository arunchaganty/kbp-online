--
-- For the crowdsourcing evaluation pipeline
--
SET search_path TO kbpo;

BEGIN TRANSACTION;

-- evaluation_mention_response
CREATE TABLE  evaluation_mention_response (
  assignment_id TEXT NOT NULL REFERENCES mturk_assignment,
  doc_id TEXT NOT NULL REFERENCES document,
  span INT4RANGE NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  question_batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  question_id TEXT NOT NULL,

  canonical_span INT4RANGE NOT NULL,
  mention_type TEXT NOT NULL,
  gloss TEXT,
  weight REAL NOT NULL DEFAULT 1.0, -- Score/weight given to this response

  PRIMARY KEY (assignment_id, doc_id, span),
  CONSTRAINT valid_weight CHECK (weight >= 0.0 AND weight <= 1.0),
  CONSTRAINT question_exists FOREIGN KEY (question_batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE evaluation_mention_response IS 'Table containing mentions within a document, as specified by CoreNLP';

-- evaluation_mention
CREATE TABLE  evaluation_mention (
  doc_id TEXT NOT NULL REFERENCES document,
  span INT4RANGE NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  question_batch_id INTEGER[] NOT NULL,
  question_id TEXT[] NOT NULL, -- this can be used to identify responses

  canonical_span INT4RANGE NOT NULL,
  mention_type TEXT NOT NULL,
  gloss TEXT,
  weight REAL NOT NULL DEFAULT 1.0, -- Score/weight given to this response

  PRIMARY KEY (doc_id, span),
  CONSTRAINT valid_weight CHECK (weight >= 0.0 AND weight <= 1.0)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE evaluation_mention IS 'Table containing mentions within a document, aggregated from all the responses';

-- evaluation_link_response
CREATE TABLE  evaluation_link_response (
  assignment_id TEXT NOT NULL REFERENCES mturk_assignment,
  doc_id TEXT NOT NULL REFERENCES document,
  span INT4RANGE NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  question_batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  question_id TEXT NOT NULL,

  link_name TEXT NOT NULL,
  weight REAL DEFAULT 1.0, -- Aggregated score/weight

  PRIMARY KEY (assignment_id, doc_id, span),
  CONSTRAINT valid_weight CHECK (weight >= 0.0 AND weight <= 1.0),
  CONSTRAINT question_exists FOREIGN KEY (question_batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE evaluation_link_response IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX evaluation_link_response_mention_idx ON evaluation_link_response(doc_id, span);

-- evaluation_link
CREATE TABLE  evaluation_link (
  doc_id TEXT NOT NULL REFERENCES document,
  span INT4RANGE NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  question_batch_id INTEGER[] NOT NULL,
  question_id TEXT[] NOT NULL, -- this can be used to identify responses

  link_name TEXT NOT NULL,
  weight REAL DEFAULT 1.0, -- Aggregated score/weight

  PRIMARY KEY (doc_id, span),
  CONSTRAINT valid_weight CHECK (weight >= 0.0 AND weight <= 1.0)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE evaluation_link IS 'Table containing mentions within a document, aggregated from all the responses';

-- evaluation_relation_response
-- evaluation_relation
CREATE TABLE  evaluation_relation_response (
  assignment_id TEXT NOT NULL REFERENCES mturk_assignment,
  doc_id TEXT NOT NULL REFERENCES document,
  subject INT4RANGE NOT NULL,
  object INT4RANGE NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  question_batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  question_id TEXT NOT NULL,

  relation TEXT NOT NULL,
  weight REAL DEFAULT 1.0, -- Aggregated score/weight

  PRIMARY KEY (assignment_id, doc_id, subject, object),
  CONSTRAINT valid_weight CHECK (weight >= 0.0 AND weight <= 1.0),
  CONSTRAINT question_exists FOREIGN KEY (question_batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE evaluation_relation_response IS 'Table containing mentions within a document, as specified by CoreNLP';
CREATE INDEX evaluation_relation_response_pair_idx ON evaluation_relation_response(doc_id, subject, object);

-- evaluation_relation
CREATE TABLE  evaluation_relation (
  doc_id TEXT NOT NULL REFERENCES document,
  subject INT4RANGE NOT NULL,
  object INT4RANGE NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  question_batch_id INTEGER[] NOT NULL,
  question_id TEXT[] NOT NULL, -- this can be used to identify responses

  relation TEXT NOT NULL,
  weight REAL DEFAULT 1.0, -- Aggregated score/weight

  PRIMARY KEY (doc_id, subject, object),
  CONSTRAINT valid_weight CHECK (weight >= 0.0 AND weight <= 1.0)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE evaluation_relation IS 'Table containing mentions within a document, aggregated from all the responses';
CREATE INDEX evaluation_relation_pair_idx ON evaluation_relation(doc_id, object);

CREATE MATERIALIZED VIEW submission_entries AS (
    SELECT 
    r.submission_id,
    r.doc_id,
    d.title,
    t.tag AS corpus_tag,
    s.gloss AS sentence,
    s.span AS sentence_span,
    m.span AS subject_span,
    m.mention_type AS subject_type,
    m.gloss AS subject_gloss,
    ml.link_name AS subject_link,
    eml.link_name AS subject_link_gold,
    lower(ml.link_name) = wikify(lower(COALESCE(eml.link_name, ml.link_name))) AS subject_link_correct,
    em.weight > 0.5 AS subject_correct,
    n.span AS object_span,
    n.mention_type AS object_type,
    n.gloss AS object_gloss,
    nl.link_name AS object_link,
    enl.link_name AS object_link_gold,
    lower(nl.link_name) = wikify(lower(COALESCE(enl.link_name, nl.link_name))) AS object_link_correct,
    en.weight > 0.5 AS object_correct,
    r.relation AS predicate_name,
    er.relation AS predicate_gold
    FROM submission_relation r
    JOIN submission_mention m ON (r.submission_id = m.submission_id AND r.doc_id = m.doc_id AND r.subject = m.span)
    JOIN submission_mention n ON (r.submission_id = n.submission_id AND r.doc_id = n.doc_id AND r.object = n.span)
    JOIN submission_link ml ON (m.submission_id = ml.submission_id AND m.doc_id = ml.doc_id AND m.canonical_span = ml.span)
    JOIN submission_link nl ON (n.submission_id = nl.submission_id AND n.doc_id = nl.doc_id AND n.canonical_span = nl.span)
    JOIN evaluation_relation er  ON (r.doc_id = er.doc_id AND r.subject = er.subject AND r.object = er.object)
    JOIN evaluation_mention em ON (m.doc_id = em.doc_id AND m.span = em.span)
    JOIN evaluation_mention en ON (n.doc_id = en.doc_id AND n.span = en.span)
    LEFT JOIN evaluation_link eml ON (ml.doc_id = eml.doc_id AND ml.span = eml.span AND eml.weight > 0.5)
    LEFT JOIN evaluation_link enl ON (nl.doc_id = enl.doc_id AND nl.span = enl.span AND enl.weight > 0.5)
    JOIN sentence s ON (s.doc_id = r.doc_id AND s.span @> r.subject)
    JOIN document d ON (r.doc_id = d.id)
    JOIN document_tag t ON (r.doc_id = t.doc_id)
    ORDER BY r.doc_id, r.subject, r.object
);

COMMIT;

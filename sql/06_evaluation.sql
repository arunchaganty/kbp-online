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
  created TIMESTAMP NOT NULL,

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

COMMIT;

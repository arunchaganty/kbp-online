--
-- For the crowdsourcing evaluation pipeline
--
SET search_path TO kbpo;

BEGIN TRANSACTION;

CREATE TYPE HIT_STATUS AS ENUM (
    'Submitted' , 
    'Approved' , 
    'Rejected'
);

CREATE SEQUENCE evaluation_batch_id_seq;
CREATE TABLE  evaluation_batch (
  id INTEGER PRIMARY KEY DEFAULT nextval('evaluation_batch_id_seq'),
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  batch_type TEXT NOT NULL, -- which type of batch is this?
  corpus_tag TEXT NOT NULL, -- which corpus.
  params JSON NOT NULL, -- the parameters used to create this batch the mturk tasks
  description TEXT -- A string blob about what this batch is for.
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE evaluation_batch IS 'Keeps track of each distinct batch of questions that have been created according to a specific sampling scheme';

CREATE TABLE  evaluation_question (
  id TEXT, -- provided by script -- is a hash of evaluation_type and parameters.
  batch_id INTEGER NOT NULL REFERENCES evaluation_batch,

  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
  params JSON NOT NULL, -- the parameters used for this question
  PRIMARY KEY (batch_id, id)
); -- DISTRIBUTED BY (batch_id);
COMMENT ON TABLE evaluation_question IS 'Keeps track of an individual question part of an evaluation batch';

CREATE SEQUENCE mturk_batch_id_seq;
CREATE TABLE  mturk_batch (
  id INTEGER PRIMARY KEY DEFAULT nextval('mturk_batch_id_seq'),
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  params JSON NOT NULL, -- the parameters used to launch the mturk tasks
  description TEXT -- A string blob about what this batch is for.
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE mturk_batch IS 'Keeps track of each distinct batch of mturk HITS';

CREATE TABLE  mturk_hit (
  id TEXT, -- provided by mturk
  batch_id INTEGER NOT NULL REFERENCES mturk_batch,

  question_batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  question_id TEXT NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  type_id TEXT, -- provided by mturk
  price REAL, -- provided to mturk
  units INTEGER, -- provided to mturk

  PRIMARY KEY(batch_id, id),
  CONSTRAINT question_exists FOREIGN KEY (question_batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (batch_id);
COMMENT ON TABLE mturk_hit IS 'Keeps track of an individual hit';

-- evaluation_request
CREATE TABLE  mturk_assignment (
  id TEXT PRIMARY KEY, -- provided by mturk
  batch_id INTEGER NOT NULL REFERENCES mturk_batch,
  hit_id TEXT NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  worker_id TEXT NOT NULL, -- provided by mturk
  worker_time INTEGER NOT NULL, -- provided by mturk (in seconds)
  status HIT_STATUS NOT NULL, -- Have we paid the turker?
  response JSON NOT NULL, -- the raw response by the worker.
  comments TEXT, -- comments provided by the turker 
  ignored BOOLEAN NOT NULL DEFAULT FALSE, -- Should we ignore this entry for some reason?
  CONSTRAINT mturk_hit_exists FOREIGN KEY (batch_id, hit_id) REFERENCES mturk_hit
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE mturk_assignment IS 'Keeps track HIT responses from turkers';

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

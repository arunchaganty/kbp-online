-- Handling how tasks are executed.
SET search_path TO kbpo;

BEGIN TRANSACTION;

CREATE SEQUENCE evaluation_batch_id_seq;
CREATE TABLE  evaluation_batch (
  id INTEGER PRIMARY KEY DEFAULT nextval('evaluation_batch_id_seq'),
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  batch_type TEXT NOT NULL, -- which type of batch is this?
  corpus_tag TEXT NOT NULL, -- which corpus.
  description TEXT -- A string blob about what this batch is for.
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE evaluation_batch IS 'Keeps track of each distinct batch of questions that have been created according to a specific sampling scheme';

CREATE TABLE evaluation_question (
  id TEXT, -- provided by script -- is a hash of evaluation_type and parameters.
  batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  -- state can be "pending-turk", "pending-response",
  -- "pending-exhaustive", etc. "done" is resereved.
  state TEXT NOT NULL, 

  params JSON NOT NULL, -- the parameters used for this question
  PRIMARY KEY (batch_id, id)
); -- DISTRIBUTED BY (batch_id);
COMMENT ON TABLE evaluation_question IS 'Keeps track of an individual question part of an evaluation batch';

CREATE TABLE evaluation_doc_question (
  question_id TEXT, 
  batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  doc_id TEXT NOT NULL,

  PRIMARY KEY (batch_id, question_id),
  CONSTRAINT evaluation_doc_question_fkey FOREIGN KEY (batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (batch_id);
COMMENT ON TABLE evaluation_doc_question IS 'Keeps track of an individual question part of an evaluation batch';

CREATE TABLE evaluation_mention_question (
  question_id TEXT, 
  batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  doc_id TEXT NOT NULL,
  span INT4RANGE NOT NULL,

  PRIMARY KEY (batch_id, question_id),
  CONSTRAINT evaluation_mention_question_fkey FOREIGN KEY (batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (batch_id);
COMMENT ON TABLE evaluation_mention_question IS 'Keeps track of an individual question part of an evaluation batch';

CREATE TABLE evaluation_relation_question (
  question_id TEXT, 
  batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  doc_id TEXT NOT NULL,
  subject INT4RANGE NOT NULL,
  object INT4RANGE NOT NULL,

  PRIMARY KEY (batch_id, question_id),
  CONSTRAINT evaluation_relation_question_fkey FOREIGN KEY (batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (batch_id);
COMMENT ON TABLE evaluation_relation_question IS 'Keeps track of an individual question part of an evaluation batch';

CREATE TYPE HIT_STATUS AS ENUM (
    'Submitted' , 
    'Approved' , 
    'Rejected'
);

CREATE SEQUENCE mturk_batch_id_seq;
CREATE TABLE  mturk_batch (
  id INTEGER PRIMARY KEY DEFAULT nextval('mturk_batch_id_seq'),
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  params JSON NOT NULL, -- the parameters used to launch the mturk tasks
  description TEXT -- A string blob about what this batch is for.
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE mturk_batch IS 'Keeps track of each distinct batch of mturk HITS';

CREATE TABLE  mturk_hit (
  id TEXT PRIMARY KEY, -- provided by mturk
  batch_id INTEGER NOT NULL REFERENCES mturk_batch,

  question_batch_id INTEGER NOT NULL REFERENCES evaluation_batch,
  question_id TEXT NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  type_id TEXT, -- provided by mturk
  price REAL, -- provided to mturk
  units INTEGER, -- provided to mturk

  CONSTRAINT question_exists FOREIGN KEY (question_batch_id, question_id) REFERENCES evaluation_question
); -- DISTRIBUTED BY (batch_id);
COMMENT ON TABLE mturk_hit IS 'Keeps track of an individual hit';

-- evaluation_request
CREATE TABLE  mturk_assignment (
  id TEXT PRIMARY KEY, -- provided by mturk
  batch_id INTEGER NOT NULL REFERENCES mturk_batch,
  hit_id TEXT NOT NULL REFERENCES mturk_hit,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  worker_id TEXT NOT NULL, -- provided by mturk
  worker_time INTEGER NOT NULL, -- provided by mturk (in seconds)
  status HIT_STATUS NOT NULL, -- Have we paid the turker?
  response JSON NOT NULL, -- the raw response by the worker.
  comments TEXT, -- comments provided by the turker 
  ignored BOOLEAN NOT NULL DEFAULT FALSE, -- Should we ignore this entry for some reason?
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE mturk_assignment IS 'Keeps track HIT responses from turkers';

COMMIT;

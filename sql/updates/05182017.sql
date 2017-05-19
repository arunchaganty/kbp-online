-- remove params from evaluation_batch.
-- add state to evaluation_question.
-- add evaluation_(doc|mention|relation)_question

BEGIN TRANSACTION;

ALTER TABLE evaluation_batch DROP COLUMN params;
ALTER TABLE evaluation_question ADD COLUMN state TEXT;

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

COMMIT;


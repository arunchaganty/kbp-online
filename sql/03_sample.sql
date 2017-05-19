-- Sampling routines
SET search_path TO kbpo;
BEGIN TRANSACTION;

CREATE SEQUENCE sample_batch_id_seq;
CREATE TABLE sample_batch (
  id INTEGER PRIMARY KEY DEFAULT nextval('sample_batch_id_seq'),
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  submission_id INTEGER REFERENCES submission(id), -- if NULL, corresponds to an exhaustive sample
  distribution_type TEXT NOT NULL, -- which type of sampling distribution is this? Useful when presenting results.
  corpus_tag TEXT NOT NULL, -- which corpus.
  params JSON NOT NULL -- the parameters used to create this batch
); -- DISTRIBUTED BY (id);
COMMENT ON TABLE sample_batch IS 'Keeps track of each distinct batch of samples drawn from a system';

CREATE TABLE document_sample (
  batch_id INTEGER NOT NULL REFERENCES sample_batch(id),
  doc_id TEXT NOT NULL REFERENCES document(id),
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  PRIMARY KEY (doc_id, batch_id)
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE document_sample IS 'Keeps track of exhaustively sampled documents';

CREATE TABLE submission_sample (
  batch_id INTEGER NOT NULL REFERENCES sample_batch(id),
  submission_id INTEGER NOT NULL REFERENCES submission(id),
  doc_id TEXT NOT NULL REFERENCES document(id),
  subject INT4RANGE NOT NULL,
  object INT4RANGE NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

  PRIMARY KEY (submission_id, doc_id, subject, object, batch_id),
  CONSTRAINT relation_exists FOREIGN KEY (submission_id, doc_id, subject, object) REFERENCES submission_relation
); -- DISTRIBUTED BY (doc_id);
COMMENT ON TABLE document_sample IS 'Keeps track of selectively sampled relations';

COMMIT;

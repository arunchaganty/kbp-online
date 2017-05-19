SET search_path TO kbpo;

CREATE OR REPLACE VIEW mturk_hit_flat AS (
  SELECT hit.*, params, description 
  FROM mturk_hit AS hit, mturk_batch AS batch 
  WHERE hit.batch_id = batch.id
);

CREATE OR REPLACE VIEW mturk_assignment_readable AS (
  SELECT id, batch_id, hit_id, created, worker_id, worker_time, status, ignored 
  FROM mturk_assignment
);

CREATE OR REPLACE VIEW mturk_assignment_flat AS (
  SELECT assignment.*, question_batch_id, question_id, type_id, price, units, params 
  FROM mturk_assignment AS assignment, mturk_hit AS hit, mturk_batch AS batch 
  WHERE hit.batch_id = batch.id AND assignment.hit_id = hit.id
);

CREATE OR REPLACE VIEW mturk_assignment_flat_readable AS (
  SELECT assignment.id AS assignment_id, hit_id, assignment.batch_id, question_batch_id, batch_type, question_id, assignment.created, worker_id, worker_time, status, ignored, type_id, price, units, batch.params, batch.description
  FROM mturk_assignment AS assignment, mturk_hit AS hit, mturk_batch AS batch, evaluation_batch AS eval_batch  
  WHERE hit.batch_id = batch.id AND assignment.hit_id = hit.id AND question_batch_id = eval_batch.id
);

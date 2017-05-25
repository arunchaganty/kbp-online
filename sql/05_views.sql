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

DROP VIEW mturk_assignment_flat CASCADE;
CREATE OR REPLACE VIEW mturk_assignment_flat AS (
  SELECT assignment.*, 
         hit.type_id, 
         hit.price, 
         hit.units,
         batch.params AS mturk_batch_params, 
         batch.description AS mturk_batch_description, 
         question.params AS question_params,
         eval_batch.id AS question_batch_id,
         eval_batch.batch_type,
         eval_batch.corpus_tag, 
         eval_batch.params AS eval_params,
         eval_batch.description AS eval_description,
         question.id AS question_id
  FROM mturk_assignment AS assignment
  LEFT JOIN mturk_hit AS hit ON assignment.hit_id = hit.id
  LEFT JOIN mturk_batch AS batch ON hit.batch_id = batch.id
  LEFT JOIN evaluation_question AS question ON question.id = hit.question_id AND question.batch_id = hit.question_batch_id
  LEFT JOIN evaluation_batch AS eval_batch ON question.batch_id = eval_batch.id
);

CREATE OR REPLACE VIEW mturk_assignment_flat_readable AS (
  SELECT assignment.id AS assignment_id, hit_id, assignment.batch_id, question_batch_id, batch_type, question_id, assignment.created, worker_id, worker_time, status, ignored, type_id, price, units, batch.params, batch.description
  FROM mturk_assignment AS assignment, mturk_hit AS hit, mturk_batch AS batch, evaluation_batch AS eval_batch
  WHERE hit.batch_id = batch.id AND assignment.hit_id = hit.id AND question_batch_id = eval_batch.id
);

DROP VIEW evaluation_mention_response_flat CASCADE;
CREATE OR REPLACE VIEW evaluation_mention_response_flat AS (
    SELECT 
     response.assignment_id,
     response.doc_id,
     response.span,
     --response.created,
     --response.question_batch_id,
     --response.question_id,
     response.canonical_span,
     response.mention_type,
     response.gloss,
     response.weight,
    assignment.*
    FROM evaluation_mention_response AS response 
    LEFT JOIN mturk_assignment_flat AS assignment ON response.assignment_id = assignment.id 
);


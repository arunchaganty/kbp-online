SET search_path TO kbpo;

DROP VIEW mturk_hit_flat;
CREATE OR REPLACE VIEW mturk_hit_flat
AS SELECT hit.*, params, description FROM mturk_hit as hit, mturk_batch as batch WHERE hit.batch_id = batch.id;

--CREATE OR REPLACE VIEW mturk_hit_status
--AS SELECT id, params->'max_assignments' - retrieved mturk_hit_with_params JOIN (SELECT hit_id, count(*) as retrieved FROM mturk_assignment GROUP BY hit_id) as retrieved_assignments ON (mturk_hit_with_params.id = retrieved_assignments.hit_id)

DROP VIEW mturk_assignment_readable;
CREATE OR REPLACE VIEW mturk_assignment_readable AS
SELECT id, batch_id, hit_id, created, worker_id, worker_time, status, ignored FROM mturk_assignment;

DROP VIEW mturk_assignment_flat;
CREATE OR REPLACE VIEW mturk_assignment_flat
AS SELECT assignment.*, question_batch_id, question_id, type_id, price, units, params FROM mturk_assignment as assignment, mturk_hit as hit, mturk_batch as batch WHERE hit.batch_id = batch.id AND assignment.hit_id = hit.id;

DROP VIEW mturk_assignment_flat_readable;
CREATE OR REPLACE VIEW mturk_assignment_flat_readable
AS SELECT assignment.id as assignment_id, hit_id, assignment.batch_id, question_batch_id, batch_type, question_id, assignment.created, worker_id, worker_time, status, ignored, type_id, price, units, batch.params, batch.description FROM mturk_assignment as assignment, mturk_hit as hit, mturk_batch as batch, evaluation_batch AS eval_batch  WHERE hit.batch_id = batch.id AND assignment.hit_id = hit.id AND question_batch_id = eval_batch.id;

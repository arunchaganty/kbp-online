-- Get all evaluation questions.
DROP TABLE IF EXISTS _evaluation_question;
CREATE TEMPORARY TABLE _evaluation_question AS (
    (SELECT question_id, question_batch_id FROM evaluation_mention_response)
    UNION
    (SELECT question_id, question_batch_id FROM evaluation_link_response)
    UNION
    (SELECT question_id, question_batch_id FROM evaluation_relation_response)
);
-- Get their batches.
DROP TABLE IF EXISTS _evaluation_batch;
CREATE TEMPORARY TABLE _evaluation_batch AS (
    SELECT DISTINCT question_batch_id FROM _evaluation_question
);

-- Get their 
DROP TABLE IF EXISTS _mturk_hit;
CREATE TEMPORARY TABLE _mturk_hit AS (
    SELECT id, batch_id FROM mturk_hit q, _evaluation_question qq WHERE q.question_id = qq.question_id AND q.question_batch_id = qq.question_batch_id
);

DROP TABLE IF EXISTS _mturk_batch;
CREATE TEMPORARY TABLE _mturk_batch AS (
    SELECT DISTINCT batch_id FROM _mturk_hit q
);


-- Output all of these.
\COPY (SELECT * FROM evaluation_question q, _evaluation_question qq WHERE q.id = qq.question_id AND q.batch_id = qq.question_batch_id) TO 'evaluation_question.tsv' CSV HEADER DELIMITER E'\t';
\COPY (SELECT * FROM evaluation_batch q, _evaluation_batch qq WHERE q.id = qq.question_batch_id) TO 'evaluation_batch.tsv' CSV HEADER DELIMITER E'\t';
\COPY (SELECT * FROM mturk_hit q, _mturk_hit qq WHERE q.id = qq.id AND q.batch_id = qq.batch_id) TO 'mturk_hit.tsv' CSV HEADER DELIMITER E'\t';
\COPY (SELECT * FROM mturk_batch q, _mturk_batch qq WHERE q.id = qq.batch_id) TO 'mturk_batch.tsv' CSV HEADER DELIMITER E'\t';

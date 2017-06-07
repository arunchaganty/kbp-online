BEGIN TRANSACTION;

TRUNCATE sample_batch CASCADE;
-- document_sample
COPY sample_batch (id, distribution_type, corpus_tag, params) FROM STDIN;
1	random	edl2016	{"type": "exhaustive"}
2	entity	kbp2016	{"type": "exhaustive"}
\.

-- submission_sample
COPY sample_batch (id, submission_id, distribution_type, corpus_tag, params) FROM STDIN;
3	1	entity	kbp2016	{"tye": "entity", "with_replacement": false}
4	1	relation	kbp2016	{"tye": "relation", "with_replacement": false}
5	2	entity	kbp2016	{"tye": "entity", "with_replacement": false}
6	2	relation	kbp2016	{"tye": "relation", "with_replacement": false}
7	3	entity	kbp2016	{"tye": "entity", "with_replacement": false}
8	3	relation	kbp2016	{"tye": "relation", "with_replacement": false}
\.

ALTER SEQUENCE sample_batch_id_seq RESTART 8;

-- Loads data into _sample tables.
INSERT INTO document_sample (batch_id, doc_id) (
    SELECT DISTINCT 1, params ->> 'doc_id'
    FROM evaluation_question
    WHERE params ->> 'batch_type' = 'exhaustive_entities'
      AND batch_id = 1
);
INSERT INTO document_sample (batch_id, doc_id) (
    SELECT DISTINCT 2, params ->> 'doc_id'
    FROM evaluation_question
    WHERE params ->> 'batch_type' = 'exhaustive_entities'
      AND batch_id = 3
);

CREATE TEMPORARY TABLE submission_sample_ (LIKE submission_sample) ON COMMIT DROP;
ALTER TABLE submission_sample_ DROP COLUMN created;

INSERT INTO submission_sample_ (batch_id, submission_id, doc_id, subject, object) (
    SELECT 3 AS batch_id,
           1 AS submission_id,
           params->>'doc_id' AS doc_id,
           int4range((params#>>'{mention_1,1}')::integer, (params#>>'{mention_1,2}')::integer) AS subject,
           int4range((params#>>'{mention_2,1}')::integer, (params#>>'{mention_2,2}')::integer) AS object
    FROM evaluation_question q
    WHERE params->>'batch_type' = 'selective_relations'
      AND batch_id = 7
);
INSERT INTO submission_sample_ (batch_id, submission_id, doc_id, subject, object) (
    SELECT 4 AS batch_id,
           1 AS submission_id,
           params->>'doc_id' AS doc_id,
           int4range((params#>>'{mention_1,1}')::integer, (params#>>'{mention_1,2}')::integer) AS subject,
           int4range((params#>>'{mention_2,1}')::integer, (params#>>'{mention_2,2}')::integer) AS object
    FROM evaluation_question 
    WHERE params->>'batch_type' = 'selective_relations'
      AND batch_id = 8
);

INSERT INTO submission_sample_ (batch_id, submission_id, doc_id, subject, object) (
    SELECT 5 AS batch_id,
           2 AS submission_id,
           params->>'doc_id' AS doc_id,
           int4range((params#>>'{mention_1,1}')::integer, (params#>>'{mention_1,2}')::integer) AS subject,
           int4range((params#>>'{mention_2,1}')::integer, (params#>>'{mention_2,2}')::integer) AS object
    FROM evaluation_question 
    WHERE params->>'batch_type' = 'selective_relations'
      AND batch_id = 11
);

INSERT INTO submission_sample_ (batch_id, submission_id, doc_id, subject, object) (
    SELECT 6 AS batch_id,
           2 AS submission_id,
           params->>'doc_id' AS doc_id,
           int4range((params#>>'{mention_1,1}')::integer, (params#>>'{mention_1,2}')::integer) AS subject,
           int4range((params#>>'{mention_2,1}')::integer, (params#>>'{mention_2,2}')::integer) AS object
    FROM evaluation_question 
    WHERE params->>'batch_type' = 'selective_relations'
      AND batch_id = 12
);


INSERT INTO submission_sample_ (batch_id, submission_id, doc_id, subject, object) (
    SELECT 7 AS batch_id,
           3 AS submission_id,
           params->>'doc_id' AS doc_id,
           int4range((params#>>'{mention_1,1}')::integer, (params#>>'{mention_1,2}')::integer) AS subject,
           int4range((params#>>'{mention_2,1}')::integer, (params#>>'{mention_2,2}')::integer) AS object
    FROM evaluation_question 
    WHERE params->>'batch_type' = 'selective_relations'
      AND batch_id = 9
);

INSERT INTO submission_sample_ (batch_id, submission_id, doc_id, subject, object) (
    SELECT 8 AS batch_id,
           3 AS submission_id,
           params->>'doc_id' AS doc_id,
           int4range((params#>>'{mention_1,1}')::integer, (params#>>'{mention_1,2}')::integer) AS subject,
           int4range((params#>>'{mention_2,1}')::integer, (params#>>'{mention_2,2}')::integer) AS object
    FROM evaluation_question 
    WHERE params->>'batch_type' = 'selective_relations'
      AND batch_id = 10
);

INSERT INTO submission_sample(batch_id, submission_id, doc_id, subject, object) (
    SELECT s.batch_id, s.submission_id, s.doc_id, s.subject, s.object
    FROM submission_sample_ s, submission_relation r
    WHERE s.submission_id = r.submission_id AND s.doc_id = r.doc_id AND s.subject = r.subject AND s.object = r.object
);

COMMIT;

BEGIN TRANSACTION;

CREATE SEQUENCE corpus_state_id_seq;
CREATE TABLE corpus_state (
    id INTEGER PRIMARY KEY DEFAULT nextval('corpus_state_id_seq'),
    corpus_tag TEXT NOT NULL,
    state TEXT NOT NULL
);

COPY corpus_state (corpus_tag, state) FROM STDIN;
kbp2016	done
edl2016	done
\.

CREATE VIEW evaluation_doc_question AS (
    SELECT q.id,
           q.batch_id,
           q.created,
           q.params->>'doc_id' AS doc_id
    FROM evaluation_question q, evaluation_batch b
    WHERE q.batch_id = b.id
      AND b.batch_type = 'exhaustive_entities'
      AND state <> 'done'
);

CREATE VIEW evaluation_relation_question AS (
    SELECT q.id,
           q.batch_id,
           q.created,
           q.params->>'doc_id' AS doc_id,
           int4range((params#>>'{mention_1,1}')::integer, (params#>>'{mention_1,2}')::integer) AS subject,
           int4range((params#>>'{mention_2,1}')::integer, (params#>>'{mention_2,2}')::integer) AS object
    FROM evaluation_question q, evaluation_batch b
    WHERE q.batch_id = b.id
      AND b.batch_type = 'selective_relations'
      AND state <> 'done'
);

COMMIT;

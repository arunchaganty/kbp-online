--
-- For the crowdsourcing evaluation pipeline
--
SET search_path TO kbpo;

BEGIN TRANSACTION;

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

  link_name TEXT, -- can be wiki:<wiki_link> or gloss:<canonical_gloss> or NULL
  correct BOOLEAN NOT NULL, --whether the link was judged to be correct or incorrect
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

  link_name TEXT NOT NULL, -- can be wiki:<wiki_link> or gloss:<canonical_gloss> or wiki:NULL
  -- implicit constraint is that wiki:NULL exists only if no other wiki link is correct
  correct BOOLEAN NOT NULL, --whether the link was judged to be correct or incorrect
  weight REAL DEFAULT 1.0, -- Aggregated score/weight
  correct BOOLEAN,

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
  created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),

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

DROP MATERIALIZED VIEW IF EXISTS evaluation_mention_link CASCADE;
CREATE MATERIALIZED VIEW evaluation_mention_link AS (
 SELECT 
    m.doc_id,
    m.span,
    m.mention_type,
    m.gloss,
    CASE
        WHEN m.mention_type = 'TITLE' THEN 'gloss:' || m.gloss
        WHEN m.mention_type = 'DATE' THEN COALESCE(l.link_name, 'date:' || m.gloss)
        ELSE COALESCE(l.link_name, 'gloss:' || m.gloss)
    END AS entity,
    m.weight AS mention_weight,
    l.weight AS link_weight,
    l.correct AS link_correct
   FROM evaluation_mention m 
   LEFT JOIN evaluation_link l ON m.doc_id = l.doc_id AND (m.span = l.span)
);

DROP MATERIALIZED VIEW IF EXISTS evaluation_entity_relation;
CREATE MATERIALIZED VIEW evaluation_entity_relation AS (
 SELECT 
    r.doc_id,
    r.subject,
    r.object,
    m.mention_type AS subject_type,
    n.mention_type AS object_type,
    m.entity AS subject_entity,
    n.entity AS object_entity,
    m.link_correct AS subject_entity_correct, -- could be null
    n.link_correct AS object_entity_correct,  -- could be null
    r.relation,
    r.weight AS relation_weight
   FROM evaluation_relation r
     JOIN evaluation_mention_link m ON r.doc_id = m.doc_id AND r.subject = m.span
     JOIN evaluation_mention_link n ON r.doc_id = n.doc_id AND r.object = n.span
);

DROP MATERIALIZED VIEW IF EXISTS submission_entries_list CASCADE;
CREATE MATERIALIZED VIEW submission_entries_list AS (
    SELECT
    -- Keys
    r.submission_id,
    r.doc_id,
    r.subject,
    r.object,

    -- Entity linking stuff
    r.subject_type,
    r.subject_gloss,
    r.subject_canonical_gloss,
    r.subject_entity,

    r.object_type,
    r.object_gloss,
    r.object_canonical_gloss,
    r.object_entity,

    -- Relations
    r.relation AS predicate_name,
    er.relation AS predicate_gold,

    -- Labels
    r.subject_type = er.subject_type AS subject_type_match,
    r.object_type = er.object_type AS object_type_match,

    r.subject_entity = er.subject_entity OR r.subject_canonical_gloss = er.subject_entity AS subject_entity_match,
    er.subject_entity_correct AS matched_subject_entity_correct,
    r.object_entity = er.object_entity OR r.object_canonical_gloss = er.object_entity AS object_entity_match,
    er.object_entity_correct AS matched_object_entity_correct,

    r.relation = er.relation AS predicate_correct

    FROM submission_entity_relation r
    -- In the current format of the linking, we have two rows, one for
    -- the entity link, and the other for the entity gloss
    -- match OR the subject's canonical gloss will match. 
    JOIN evaluation_entity_relation er ON (r.doc_id = er.doc_id AND r.subject = er.subject AND r.object = er.object)
);

DROP MATERIALIZED VIEW IF EXISTS submission_entries;
CREATE MATERIALIZED VIEW submission_entries AS (
    WITH _null_columns AS (
        SELECT *,
            CASE 
                WHEN subject_type_match AND subject_entity_match THEN matched_subject_entity_correct 
                ELSE NULL 
            END AS subject_entity_correct,

            CASE 
                WHEN object_type_match AND object_entity_match THEN matched_object_entity_correct 
                ELSE NULL 
            END AS object_entity_correct,

            CASE 
                WHEN subject_type_match AND object_type_match THEN predicate_correct
                ELSE NULL 
            END AS matched_predicate_correct
        FROM submission_entries_list)
    SELECT DISTINCT ON (r.submission_id, r.doc_id, r.subject, r.object)
    -- Document viewing stuff
    d.title,
    t.tag AS corpus_tag,
    s.gloss AS sentence,
    s.span AS sentence_span,

    -- Keys
    r.*,

    -- Labels
    r.matched_subject_entity_correct AND r.matched_object_entity_correct  AND r.matched_predicate_correct AS correct

    FROM 
    _null_columns r
    JOIN sentence s ON (s.doc_id = r.doc_id AND s.span @> r.subject)
    JOIN document d ON (r.doc_id = d.id)
    JOIN document_tag t ON (r.doc_id = t.doc_id)
    ORDER BY r.submission_id, r.doc_id, r.subject, r.object,
            subject_type_match DESC, object_type_match DESC,
            subject_entity_match DESC, object_entity_match DESC,
            r.subject_entity_correct, r.object_entity_correct  
);

COMMIT;

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
        WHEN m.mention_type = 'TITLE' THEN m.gloss
        ELSE COALESCE(l.link_name, m.gloss)
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

DROP MATERIALIZED VIEW IF EXISTS submission_entries;
CREATE MATERIALIZED VIEW submission_entries AS (
    WITH _valid_entries AS (SELECT DISTINCT
        r.submission_id, r.doc_id, r.subject, r.object
        FROM submission_entity_relation r
        -- In the current format of the linking, we have two rows, one for
        -- the entity link, and the other for the entity gloss
        -- match OR the subject's canonical gloss will match. 
        JOIN evaluation_entity_relation er ON (r.doc_id = er.doc_id AND r.subject = er.subject AND r.object = er.object)
    )
    SELECT DISTINCT ON (r.submission_id, r.doc_id, r.subject, r.object)
    -- Keys
    r.submission_id,
    r.doc_id,
    r.subject,
    r.object,

    -- Document viewing stuff
    d.title,
    t.tag AS corpus_tag,
    s.gloss AS sentence,
    s.span AS sentence_span,

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
    er.subject_entity_correct,
    er.object_entity_correct,
    r.relation = er.relation AS predicate_correct,
    CASE  -- When something is wrong, we know it is wrong!
        WHEN NOT (COALESCE(er.subject_entity_correct, true) 
             AND COALESCE(er.object_entity_correct, true)
             AND r.relation = er.relation) THEN false
        ELSE -- But if it hasn't been evaluated, unfortunately, we just don't know.
            er.subject_entity_correct AND er.object_entity_correct AND r.relation = er.relation
    END AS correct

    FROM submission_entity_relation r
    -- In the current format of the linking, we have two rows, one for
    -- the entity link, and the other for the entity gloss
    -- match OR the subject's canonical gloss will match. 
    JOIN _valid_entries v ON (r.submission_id = v.submission_id AND r.doc_id = v.doc_id AND r.subject = v.subject AND r.object = v.object)
    LEFT JOIN evaluation_entity_relation er ON (r.doc_id = er.doc_id AND r.subject = er.subject AND r.object = er.object 
      AND (r.subject_entity = er.subject_entity OR 'gloss:' || r.subject_canonical_gloss = er.subject_entity)
      AND (r.object_entity = er.object_entity OR 'gloss:' || r.object_canonical_gloss = er.object_entity)
    )
    JOIN sentence s ON (s.doc_id = r.doc_id AND s.span @> r.subject)
    JOIN document d ON (r.doc_id = d.id)
    JOIN document_tag t ON (r.doc_id = t.doc_id)
    ORDER BY r.submission_id, r.doc_id, r.subject, r.object, er.subject_entity_correct, er.object_entity_correct  
);

COMMIT;

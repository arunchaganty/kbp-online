-- Migrating to transform deprecated SPAN classes to INT4RANGE
--
-- BEGIN TRANSACTION;
-- 
-- -- INSERT INTO document (SELECT * FROM kbpo_bk.document);
-- -- INSERT INTO document_tag (SELECT * FROM kbpo_bk.document_tag);
-- INSERT INTO sentence(id, updated, doc_id, span, sentence_index, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end, gloss, dependencies) (
--   SELECT id, updated, 
--       doc_id, int4range(doc_char_begin[1], doc_char_end[array_length(doc_char_end, 1)]), sentence_index,
--       words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end, gloss, dependencies
--   FROM kbpo_bk.sentence);
-- -- INSERT INTO suggested_mention(doc_id, span, updated, sentence_id, mention_type, canonical_span, gloss) (SELECT doc_id, int4range((id).char_begin, (id).char_end), updated, sentence_id, mention_type, int4range((canonical_span).char_begin, (canonical_span).char_end), gloss FROM kbpo_bk.suggested_mention_);
-- INSERT INTO suggested_link(doc_id, span, updated, link_name, confidence) (SELECT
--   doc_id, int4range((id).char_begin, (id).char_end), updated, link_name, confidence
--   FROM kbpo_bk.suggested_link);
-- 
-- COMMIT;

-- BEGIN TRANSACTION;
-- 
-- INSERT INTO submission (SELECT * FROM kbpo_bk.submission);
-- 
-- INSERT INTO submission_mention(submission_id, doc_id, span, updated, canonical_span, mention_type, gloss) (SELECT
--   submission_id, doc_id, int4range((mention_id).char_begin, (mention_id).char_end), updated,
--   int4range((canonical_id).char_begin, (canonical_id).char_end),
--   mention_type, gloss
--   FROM kbpo_bk.submission_mention);
-- 
-- INSERT INTO submission_link(submission_id, doc_id, span, updated, link_name, confidence) (SELECT
--   submission_id, doc_id, int4range((mention_id).char_begin, (mention_id).char_end), updated, link_name, confidence
--   FROM kbpo_bk.submission_link);
-- 
-- INSERT INTO submission_relation(submission_id, doc_id, subject, object, updated, relation, provenances, confidence) (SELECT
--   submission_id, doc_id,
--   int4range((subject_id).char_begin, (subject_id).char_end), int4range((object_id).char_begin, (object_id).char_end),
--   updated, relation, ARRAY[]::int4range[], confidence
--   FROM kbpo_bk.submission_relation);
-- 
-- -- INSERT INTO submission_score (SELECT * FROM kbpo_bk.submission_score);
-- 
-- COMMIT;

BEGIN TRANSACTION;

INSERT INTO evaluation_batch (SELECT id, created, batch_type, corpus_tag, params::JSON, description FROM kbpo_bk.evaluation_batch);
INSERT INTO evaluation_question (SELECT id, batch_id, created, params::JSON FROM kbpo_bk.evaluation_question);
INSERT INTO mturk_batch (SELECT id, created, params::JSON, description FROM kbpo_bk.mturk_batch);
INSERT INTO mturk_hit (SELECT id, batch_id, question_batch_id, question_id, created, type_id, price, units FROM kbpo_bk.mturk_hit);
INSERT INTO mturk_assignment (SELECT id, batch_id, hit_id, created, worker_id, worker_time, status::HIT_STATUS, response::JSON, comments, ignored FROM kbpo_bk.mturk_assignment);

INSERT INTO evaluation_mention_response(assignment_id, question_batch_id, question_id, doc_id, span, created, canonical_span, mention_type, gloss, weight) (SELECT
  assignment_id, question_batch_id, question_id, 
  doc_id, int4range((mention_id).char_begin, (mention_id).char_end), 
  created, 
  int4range((canonical_id).char_begin, (canonical_id).char_end), 
  mention_type, gloss, weight
  FROM kbpo_bk.evaluation_mention_response);

-- evaluation_mention
INSERT INTO evaluation_mention(question_batch_id, question_id, doc_id, span, created, canonical_span, mention_type, gloss, weight) (SELECT
  ARRAY[question_batch_id], ARRAY[question_id], 
  doc_id, int4range((mention_id).char_begin, (mention_id).char_end), 
  created,
  int4range((canonical_id).char_begin, (canonical_id).char_end), 
  mention_type, gloss, weight
  FROM kbpo_bk.evaluation_mention);

-- evaluation_link_response
INSERT INTO evaluation_link_response(assignment_id, question_batch_id, question_id, doc_id, span, created, link_name, weight) (SELECT
  assignment_id, question_batch_id, question_id, 
  doc_id, int4range((mention_id).char_begin, (mention_id).char_end), 
  created, 
  link_name, weight
  FROM kbpo_bk.evaluation_link_response);

-- evaluation_link
INSERT INTO evaluation_link(question_batch_id, question_id, doc_id, span, created, link_name, weight) (SELECT
  ARRAY[question_batch_id], ARRAY[question_id], 
  doc_id, int4range((mention_id).char_begin, (mention_id).char_end), 
  created,
  link_name, weight
  FROM kbpo_bk.evaluation_link);

-- evaluation_relation_response
INSERT INTO evaluation_relation_response(assignment_id, question_batch_id, question_id, doc_id, subject, object, created, relation, weight) (SELECT
  assignment_id, question_batch_id, question_id, doc_id, 
  int4range((subject_id).char_begin, (subject_id).char_end),
  int4range((object_id).char_begin, (object_id).char_end),
  created, relation, weight
  FROM kbpo_bk.evaluation_relation_response);

-- evaluation_relation
INSERT INTO evaluation_relation(question_batch_id, question_id, doc_id, subject, object, created, relation, weight) (SELECT
  array_agg(question_batch_id), array_agg(question_id), doc_id, 
  int4range((subject_id).char_begin, (subject_id).char_end) AS subject,
  int4range((object_id).char_begin, (object_id).char_end) AS object,
  min(created), min(relation), avg(weight)
  FROM kbpo_bk.evaluation_relation
  GROUP BY doc_id, subject, object
);

COMMIT;

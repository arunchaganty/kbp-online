--
-- Database types.
--
CREATE TYPE SPAN AS (
  doc_id TEXT,
  char_begin INTEGER,
  char_end INTEGER
);
COMMENT ON TYPE SPAN IS 'A span stores doc_id, doc_begin and doc_end.';

CREATE TYPE SCORE AS (
  precision REAL,
  recall REAL,
  f1 REAL
);
COMMENT ON TYPE SCORE IS 'The score contains precision, recall, f1.';

CREATE TYPE SCORE_TYPE AS ENUM (
    'entity_macro',
    'entity_micro',
    'relation_macro',
    'relation_micro',
    'instance_macro',
    'instance_micro'
);
COMMENT ON TYPE SCORE_TYPE IS 'The precise mode in which scores have been generated.';

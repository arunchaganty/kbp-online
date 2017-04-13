--
-- Database types.
--
SET search_path TO kbpo;

CREATE TYPE SPAN AS (
  doc_id TEXT NOT NULL,
  char_begin INTEGER NOT NULL,
  char_end INTEGER NULL
);
COMMENT ON TYPE SPAN IS 'A span stores doc_id, doc_begin and doc_end.';

CREATE TYPE SCORE AS (
  precision REAL,
  recall REAL,
  f1 REAL
);
COMMENT ON TYPE SCORE IS 'The score contains precision, recall, f1.';

-- FIXME: These types are not supported by postgres 8.2 that is used by
-- Greenplum.
-- CREATE TYPE SCORE_TYPE AS ENUM (
--     'entity_macro',
--     'entity_micro',
--     'relation_macro',
--     'relation_micro',
--     'instance_macro',
--     'instance_micro'
-- );
-- COMMENT ON TYPE SCORE_TYPE IS 'The precise mode in which scores have been generated.';
-- 
-- CREATE TYPE EVALUATION_TYPE AS ENUM (
--     'exhaustive_document',
--     'exhaustive_relations',
--     'selective_relations'
-- );
-- COMMENT ON TYPE EVALUATION_TYPE IS 'The type of evaluation we are using.';
-- 
-- CREATE TYPE HIT_STATUS AS ENUM (
--     'pending',
--     'accepted',
--     'rejected'
-- );
-- COMMENT ON TYPE HIT_STATUS IS 'The payment status for a HIT.';

-- Support routines for span.
CREATE FUNCTION span_overlap(x SPAN, y SPAN) RETURNS BOOLEAN AS  $$
BEGIN
    IF (x.doc_id <> y.doc_id)
          OR (x.char_end <= y.char_begin) -- Equality because spans are end exclusive.
          OR (y.char_end <= x.char_begin) THEN 
            RETURN FALSE;
    ELSE 
            RETURN TRUE;
    END IF;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION span_overlap(SPAN, SPAN) IS 'Checks that the span begin and end are not disjoint.';

CREATE FUNCTION span_disjoint(x SPAN, y SPAN) RETURNS BOOLEAN AS $$
BEGIN
    IF (x.doc_id <> y.doc_id)
          OR (x.char_end <= y.char_begin) -- Equality because spans are end exclusive.
          OR (y.char_end <= x.char_begin) THEN 
            RETURN TRUE;
    ELSE 
            RETURN FALSE;
    END IF;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION span_disjoint(SPAN, SPAN) IS 'Checks that the span begin and end are disjoint.';

CREATE FUNCTION span_contains(x SPAN, y SPAN) RETURNS BOOLEAN AS  $$
BEGIN
    IF (x.doc_id <> y.doc_id) THEN RETURN FALSE;
    ELSE
        RETURN (x.char_begin <= y.char_begin) AND (x.char_end >= y.char_begin);
    END IF;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION span_contains(SPAN, SPAN) IS 'Checks that the first span contains the 2nd.';

CREATE FUNCTION span_contained_by(x SPAN, y SPAN) RETURNS BOOLEAN AS  $$
BEGIN
    IF (x.doc_id <> y.doc_id) THEN RETURN FALSE;
    ELSE
        RETURN (y.char_begin <= x.char_begin) AND (y.char_end >= x.char_begin);
    END IF;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION span_contained_by(SPAN, SPAN) IS 'Checks that the first span contained by the 2nd.';



-- Implementation of various functions on span for postgres to be happy.
CREATE FUNCTION span_cmp(x SPAN, y SPAN) RETURNS INTEGER AS $$
BEGIN
  IF (x.doc_id < y.doc_id) THEN RETURN -1;
  ELSIF (x.doc_id > y.doc_id) THEN RETURN 1;
  ELSE
    IF (x.char_begin < y.char_begin) THEN RETURN -1;
    ELSIF (x.char_begin > y.char_begin) THEN RETURN 1;
    ELSE
      IF (x.char_end < y.char_end) THEN RETURN -1;
      ELSIF (x.char_end > y.char_end) THEN RETURN 1;
      ELSE RETURN 0;
      END IF;
    END IF;
  END IF;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION span_cmp(SPAN, SPAN) IS 'Compares two spans.';

CREATE FUNCTION span_lt(x SPAN, y SPAN) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) < 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_lte(x SPAN, y SPAN) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) <= 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_neq(x SPAN, y SPAN) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) <> 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_eq(x SPAN, y SPAN) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) = 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_gt(x SPAN, y SPAN) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) > 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_gte(x SPAN, y SPAN) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) >= 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION hashspan(x SPAN) RETURNS INTEGER AS $$
BEGIN
    RETURN hashtext(x.doc_id) + 41 * (x.char_begin) + 73 * (x.char_end);
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE OPERATOR < (
   leftarg = SPAN, rightarg = SPAN, procedure = span_lt,
   commutator = > , negator = >= ,
   restrict = scalarltsel, join = scalarltjoinsel
);

CREATE OPERATOR <= (
   leftarg = SPAN, rightarg = SPAN, procedure = span_lte,
   commutator = >= , negator = > ,
   restrict = scalarltsel, join = scalarltjoinsel
);

CREATE OPERATOR = (
   leftarg = SPAN, rightarg = SPAN, procedure = span_eq,
   commutator = = , negator = <> ,
   restrict = eqsel, join = eqjoinsel,
   hashes, merges
);

CREATE OPERATOR <> (
   leftarg = SPAN, rightarg = SPAN, procedure = span_neq,
   commutator = <> , negator = = ,
   restrict = neqsel, join = neqjoinsel
);

CREATE OPERATOR >= (
   leftarg = SPAN, rightarg = SPAN, procedure = span_gte,
   commutator = <= , negator = < ,
   restrict = scalargtsel, join = scalargtjoinsel
);

CREATE OPERATOR > (
   leftarg = SPAN, rightarg = SPAN, procedure = span_gt,
   commutator = < , negator = <= ,
   restrict = scalargtsel, join = scalargtjoinsel
);

CREATE OPERATOR CLASS span_ops
    DEFAULT FOR TYPE SPAN USING btree AS
        OPERATOR        1       < ,
        OPERATOR        2       <= ,
        OPERATOR        3       = ,
        OPERATOR        4       >= ,
        OPERATOR        5       > ,
        FUNCTION        1       span_cmp(SPAN, SPAN);

CREATE OPERATOR CLASS span_ops
    DEFAULT FOR TYPE SPAN USING hash AS
        OPERATOR        1       = ,
        FUNCTION        1       hashspan(SPAN);

CREATE OPERATOR && (
   leftarg = SPAN, rightarg = SPAN, procedure = span_overlap,
   commutator = &&,
   restrict = eqsel, join = eqjoinsel
);

CREATE TYPE EVALUATION_TYPE AS ENUM (
    'exhaustive_entities',
    'exhaustive_relations',
    'selective_relations'
);
CREATE OPERATOR @> (
   leftarg = SPAN, rightarg = SPAN, procedure = span_contains,
   commutator = <@,
   restrict = eqsel, join = eqjoinsel
);

CREATE TYPE HIT_STATUS AS ENUM (
    'Submitted' , 
    'Approved' , 
    'Rejected'
);
CREATE OPERATOR <@ (
   leftarg = SPAN, rightarg = SPAN, procedure = span_contained_by,
   commutator = @>,
   restrict = eqsel, join = eqjoinsel
);

-- -- Database types.
--
-- span type. NOTE: this script _must_ be run as superuser to be able to
-- create an operator class and hence create indices for span, etc.
--
SET search_path TO kbpo;

CREATE TYPE span AS (
  doc_id TEXT,
  char_begin INTEGER,
  char_end INTEGER
);
COMMENT ON TYPE span IS 'A span stores doc_id, doc_begin and doc_end.';

CREATE TYPE SCORE AS (
  precision REAL,
  recall REAL,
  f1 REAL
);
COMMENT ON TYPE SCORE IS 'The score contains precision, recall, f1.';

-- Support routines for span.
CREATE FUNCTION span_overlap(x span, y span) RETURNS BOOLEAN AS  $$
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
COMMENT ON FUNCTION span_overlap(span, span) IS 'Checks that the span begin and end are not disjoint.';

CREATE FUNCTION span_disjoint(x span, y span) RETURNS BOOLEAN AS $$
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
COMMENT ON FUNCTION span_disjoint(span, span) IS 'Checks that the span begin and end are disjoint.';

CREATE FUNCTION span_contains(x span, y span) RETURNS BOOLEAN AS  $$
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
COMMENT ON FUNCTION span_contains(span, span) IS 'Checks that the first span contains the 2nd.';

CREATE FUNCTION span_contained_by(x span, y span) RETURNS BOOLEAN AS  $$
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
COMMENT ON FUNCTION span_contained_by(span, span) IS 'Checks that the first span contained by the 2nd.';



-- Implementation of various functions on span for postgres to be happy.
CREATE FUNCTION span_cmp(x span, y span) RETURNS INTEGER AS $$
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
COMMENT ON FUNCTION span_cmp(span, span) IS 'Compares two spans.';

CREATE FUNCTION span_lt(x span, y span) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) < 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_lte(x span, y span) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) <= 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_neq(x span, y span) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) <> 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_eq(x span, y span) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) = 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_gt(x span, y span) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) > 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION span_gte(x span, y span) RETURNS BOOLEAN AS $$
BEGIN
  RETURN span_cmp(x, y) >= 0;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE FUNCTION hashspan(x span) RETURNS INTEGER AS $$
BEGIN
    RETURN hashtext(x.doc_id) + 41 * (x.char_begin) + 73 * (x.char_end);
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;

CREATE OR REPLACE FUNCTION as_prov(span SPAN)
RETURNS TEXT AS
$_$
BEGIN
      RETURN span.doc_id || ':' || span.char_begin || '-' || span.char_end;  
END
$_$ LANGUAGE plpgsql;


CREATE OPERATOR < (
   leftarg = span, rightarg = span, procedure = span_lt,
   commutator = > , negator = >= ,
   restrict = scalarltsel, join = scalarltjoinsel
);

CREATE OPERATOR <= (
   leftarg = span, rightarg = span, procedure = span_lte,
   commutator = >= , negator = > ,
   restrict = scalarltsel, join = scalarltjoinsel
);

CREATE OPERATOR = (
   leftarg = span, rightarg = span, procedure = span_eq,
   commutator = = , negator = <> ,
   restrict = eqsel, join = eqjoinsel,
   hashes, merges
);

CREATE OPERATOR <> (
   leftarg = span, rightarg = span, procedure = span_neq,
   commutator = <> , negator = = ,
   restrict = neqsel, join = neqjoinsel
);

CREATE OPERATOR >= (
   leftarg = span, rightarg = span, procedure = span_gte,
   commutator = <= , negator = < ,
   restrict = scalargtsel, join = scalargtjoinsel
);

CREATE OPERATOR > (
   leftarg = span, rightarg = span, procedure = span_gt,
   commutator = < , negator = <= ,
   restrict = scalargtsel, join = scalargtjoinsel
);

CREATE OPERATOR && (
   leftarg = span, rightarg = span, procedure = span_overlap,
   commutator = &&,
   restrict = eqsel, join = eqjoinsel
);

CREATE OPERATOR @> (
   leftarg = span, rightarg = span, procedure = span_contains,
   commutator = <@,
   restrict = eqsel, join = eqjoinsel
);

CREATE OPERATOR <@ (
   leftarg = span, rightarg = span, procedure = span_contained_by,
   commutator = @>,
   restrict = eqsel, join = eqjoinsel
);

CREATE OPERATOR CLASS span_ops
    DEFAULT FOR TYPE span USING btree AS
        OPERATOR        1       < ,
        OPERATOR        2       <= ,
        OPERATOR        3       = ,
        OPERATOR        4       >= ,
        OPERATOR        5       > ,
        FUNCTION        1       span_cmp(span, span);

CREATE OPERATOR CLASS span_ops
    DEFAULT FOR TYPE span USING hash AS
        OPERATOR        1       = ,
        FUNCTION        1       hashspan(span);

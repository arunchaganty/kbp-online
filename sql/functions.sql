
-- CREATE OR REPLACE FUNCTION foo(i integer) RETURNS integer AS $$
--      BEGIN
--              RETURN i + 1;
--      END;
-- $$ 
-- LANGUAGE plpgsql
-- IMMUTABLE|STABLE
-- ;
BEGIN;
CREATE FUNCTION span_is_valid(x SPAN) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN x.char_end > x.char_begin;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
;
COMMENT ON FUNCTION span_is_valid(SPAN) IS 'Checks that span ends after it begins.';

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
;
COMMENT ON FUNCTION span_overlap(SPAN, SPAN) IS 'Checks that the span begin and end are disjoint.';

COMMIT;

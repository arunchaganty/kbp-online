
-- CREATE OR REPLACE FUNCTION foo(i integer) RETURNS integer AS $$
--      BEGIN
--              RETURN i + 1;
--      END;
-- $$ 
-- LANGUAGE plpgsql
-- IMMUTABLE|STABLE
-- ;

CREATE FUNCTION span_is_valid(x SPAN) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN x.char_end > x.char_begin;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
;

CREATE FUNCTION span_overlap(x SPAN, y SPAN) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN CASE WHEN (x.doc_id <> y.doc_id)
                  OR (x.char_end < y.char_begin)
                  OR (y.char_end < x.char_begin)
                THEN FALSE
            ELSE TRUE;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
;

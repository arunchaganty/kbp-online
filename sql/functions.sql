SET search_path TO kbpo;

-- CREATE OR REPLACE FUNCTION foo(i integer) RETURNS integer AS $$
--      BEGIN
--              RETURN i + 1;
--      END;
-- $$ 
-- LANGUAGE plpgsql
-- IMMUTABLE|STABLE
-- ;
BEGIN TRANSACTION;

CREATE OR REPLACE FUNCTION is_kbpo_reln(x TEXT) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN x = 'per:alternate_names'
        OR x = 'per:place_of_birth'
        OR x = 'per:place_of_residence'
        OR x = 'per:place_of_death'
        OR x = 'per:date_of_birth'
        OR x = 'per:date_of_death'
        OR x = 'per:organizations_founded'
        OR x = 'per:holds_shares_in'
        OR x = 'per:schools_attended'
        OR x = 'per:employee_or_member_of'
        OR x = 'per:parents'
        OR x = 'per:children'
        OR x = 'per:spouse'
        OR x = 'per:sibling'
        OR x = 'per:other_family'
        OR x = 'per:title'
        OR x = 'org:alternate_names'
        OR x = 'org:place_of_headquarters'
        OR x = 'org:date_founded'
        OR x = 'org:date_dissolved'
        OR x = 'org:founded_by'
        OR x = 'org:member_of'
        OR x = 'org:members'
        OR x = 'org:subsidiaries'
        OR x = 'org:parents'
        OR x = 'org:shareholders'
        OR x = 'org:holds_shares_in'
        OR x = 'gpe:births_in_place'
        OR x = 'gpe:residents_in_place'
        OR x = 'gpe:deaths_in_place'
        OR x = 'gpe:employees_or_members'
        OR x = 'gpe:holds_shares_in'
        OR x = 'gpe:organizations_founded'
        OR x = 'gpe:member_of'
        OR x = 'gpe:headquarters_in_place'
        OR x = 'no_relation'
        ;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION is_kbpo_reln(TEXT) IS 'Checks that a reln is supported by KBPO.';


CREATE OR REPLACE FUNCTION is_kbpo_type(x TEXT) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN x = 'PER' 
        OR x = 'ORG' 
        OR x = 'GPE' 
        OR x = 'TITLE' 
        OR x = 'DATE'
        ;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION is_kbpo_type(TEXT) IS 'Checks that a type is supported by KBPO.';

CREATE OR REPLACE FUNCTION is_entity_type(x TEXT) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN x = 'PER' 
        OR x = 'ORG' 
        OR x = 'GPE'
        ;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION is_entity_type(TEXT) IS 'Checks that a type is supported by KBPO.';

CREATE OR REPLACE FUNCTION _final_mode(anyarray)
  RETURNS anyelement AS
$BODY$
    SELECT a
    FROM unnest($1) a
    GROUP BY 1 
    ORDER BY COUNT(1) DESC, 1
    LIMIT 1;
$BODY$
LANGUAGE SQL IMMUTABLE;
 
-- Tell Postgres how to use our aggregate
DROP AGGREGATE IF EXISTS mode(anyelement);

CREATE AGGREGATE mode(anyelement) (
  SFUNC=array_append, --Function to call for each row. Just builds the array
  STYPE=anyarray,
  FINALFUNC=_final_mode, --Function to call after everything has been added to array
  INITCOND='{}' --Initialize an empty array when starting
);
COMMIT;

BEGIN TRANSACTION;
CREATE OR REPLACE FUNCTION wikify(name TEXT) 
RETURNS TEXT AS
$_$
BEGIN
    RETURN translate($1, E' []{}%+|?=<>\'"\/', '_________________'); 
END
$_$ LANGUAGE plpgsql;
COMMIT;

BEGIN TRANSACTION;
-- Create a function that always returns the first non-NULL item
CREATE OR REPLACE FUNCTION public.first_agg ( anyelement, anyelement )
RETURNS anyelement LANGUAGE SQL IMMUTABLE STRICT AS $$
        SELECT $1;
$$;
 
-- And then wrap an aggregate around it
CREATE AGGREGATE public.FIRST (
        sfunc    = public.first_agg,
        basetype = anyelement,
        stype    = anyelement
);
 
-- Create a function that always returns the last non-NULL item
CREATE OR REPLACE FUNCTION public.last_agg ( anyelement, anyelement )
RETURNS anyelement LANGUAGE SQL IMMUTABLE STRICT AS $$
        SELECT $2;
$$;
 
-- And then wrap an aggregate around it
CREATE AGGREGATE public.LAST (
        sfunc    = public.last_agg,
        basetype = anyelement,
        stype    = anyelement
);
COMMIT;



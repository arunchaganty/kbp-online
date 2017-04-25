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

CREATE FUNCTION is_kbpo_reln(x TEXT) RETURNS BOOLEAN AS  $$
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


CREATE FUNCTION is_kbpo_type(x TEXT) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN x = 'PERSON' 
        OR x = 'ORGANIZATION' 
        OR x = 'COUNTRY' 
        OR x = 'LOCATION' 
        OR x = 'CITY' 
        OR x = 'STATE_OR_PROVINCE' 
        OR x = 'GPE' 
        OR x = 'TITLE' 
        OR x = 'DATE';
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION is_kbpo_type(TEXT) IS 'Checks that a type is supported by KBPO.';

CREATE FUNCTION span_is_valid(x span) RETURNS BOOLEAN AS  $$
BEGIN
    RETURN x.char_end > x.char_begin;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
STRICT
;
COMMENT ON FUNCTION span_is_valid(span) IS 'Checks that span ends after it begins.';

COMMIT;

SET search_path TO kbpo;
BEGIN TRANSACTION
\i types.sql
\i functions.sql

\i basic.sql
\i submission.sql
\i evaluation.sql
COMMIT

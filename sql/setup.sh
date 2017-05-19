#!/bin/bash
# Sets up KBPO database (minus django stuff)

if [[ $# != 2 ]]; then 
  echo "Usage: $0 <usrname> <dbname> [superusr]"
  exit 1;
fi;

usrname=$1
dbname=$2
superusr=$3

if [ ! -z $superusr ]; then
  sudo -u postgres psql $dbname -c 'CREATE SCHEMA kbpo AUTHORIZATION kbpo;'
else
  psql $dbname -c 'CREATE SCHEMA kbpo AUTHORIZATION kbpo;'
fi;

PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f '00_functions.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f '01_basic.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f '02_submission.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f '03_sample.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f '04_questions.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f '05_views.ql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f '06_evaluation.sql'

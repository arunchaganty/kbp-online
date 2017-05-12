#!/bin/bash
# Sets up KBPO database (minus django stuff)

if [[ $# != 2 ]]; then 
  echo "Usage: $0 <usrname> <dbname> <superusr>"
  exit 1;
fi;

usrname=$1
dbname=$2
superusr=$3

if [ ! -z $superusr ]; then
  sudo -u postgres psql $dbname -c 'create schema kbpo authorization kbpo;'
else
  psql $dbname -c 'create schema kbpo authorization kbpo;'
fi;

PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'functions.sql'

PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'basic.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'submission.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'evaluation.sql'

PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'views.sql'

#!/bin/bash
# Sets up KBPO database (minus django stuff)

if [[ $# != 2 ]]; then 
  echo "Usage: $0 <usrname> <dbname>"
  exit 1;
fi;

usrname=$1
dbname=$2

#sudo -u postgres psql $dbname -c 'CREATE SCHEMA kbpo AUTHORIZATION kbpo;'
#sudo -u postgres psql $dbname -f 'span.sql'
#
#PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'functions.sql'

#PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'basic.sql'
#PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'submission.sql'
PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'evaluation.sql'

PGPASSWORD=$usrname psql -h localhost -U $usrname $dbname -f 'views.sql'

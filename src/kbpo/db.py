#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database utilities.
"""

import logging
import re
import psycopg2 as db
from psycopg2.extras import execute_values
from .kbpo_db_params import _PARAMS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def connect(params=_PARAMS):
    """Connect to database using @params"""
    conn = db.connect(**params)
    with conn:
        with conn.cursor() as _cur:
            _cur.execute("SET search_path TO kbpo;")
    return conn

CONN = None

try:
    CONN = connect()
except:
    logging.error("Unable to connect to database")

def select(sql, **kwargs):
    """Wrapper around psycopg execute function to yield the result of a SELECT statement"""
    with CONN:
        with CONN.cursor() as cur:
            cur.execute(sql, kwargs)
            yield from cur

def execute(sql, **kwargs):
    """Wrapper around psycopg execute function to not yield the result of execute statement"""
    with CONN:
        with CONN.cursor() as cur:
            cur.execute(sql, kwargs)

def sanitize(word):
    """
    Remove any things that would confusing psql.
    """
    return re.sub(r"[^a-zA-Z0-9. ]", "%", word)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database utilities.
"""

import logging
import re
import psycopg2
from psycopg2.extras import execute_values, NumericRange, register_composite, Json
from .params.db.default import _PARAMS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def connect(params=_PARAMS):
    """Connect to database using @params"""
    conn = psycopg2.connect(**params)
    with conn:
        with conn.cursor() as _cur:
            _cur.execute("SET search_path TO kbpo;")
    register_composite('kbpo.score', conn, True)
    return conn

CONN = None

try:
    CONN = connect()
except:
    logging.error("Unable to connect to database")

def get(sql, cur=None, **kwargs):
    """
    Gets a single row from the SQL statement above.
    """
    if cur is None:
        with CONN:
            with CONN.cursor() as cur:
                return get(sql, cur, **kwargs)
    else:
        cur.execute(sql, kwargs)
        return cur.fetchone()

def select(sql, cur=None, **kwargs):
    """Wrapper around psycopg execute function to yield the result of a SELECT statement"""
    if cur is None:
        with CONN:
            with CONN.cursor() as cur:
                #register_composite('kbpo.score', cur)
                cur.execute(sql, kwargs)
                yield from cur
    else:
        cur.execute(sql, kwargs)
        yield from cur

def mogrify(sql, cur=None, verbose = True, **kwargs):
    """Wrapper around psycopg mogrigy function"""
    if cur is None:
        with CONN:
            with CONN.cursor() as cur:
                if verbose:
                    print(cur.mogrify(sql, kwargs))
                return cur.mogrify(sql, kwargs)
    else:
        if verbose:
            print(cur.mogrify(sql, kwargs))
        return cur.mogrify(sql, kwargs)

def execute(sql, cur=None, **kwargs):
    """Wrapper around psycopg execute function to not yield the result of execute statement"""
    if cur is None:
        with CONN:
            with CONN.cursor() as cur:
                cur.execute(sql, kwargs)
    else:
        cur.execute(sql, kwargs)

def sanitize(word):
    """
    Remove any things that would confusing psql.
    """
    return re.sub(r"[^a-zA-Z0-9. ]", "%", word)

class TypedNumericRange(NumericRange):
    pg_type = None

class Int4NumericRange(TypedNumericRange):
    pg_type = b'int4range'

class TypedNumericRangeAdapter(psycopg2._range.NumberRangeAdapter):
    def getquoted(self):
        return super(TypedNumericRangeAdapter, self).getquoted() + b'::' + self.adapted.pg_type
psycopg2.extensions.register_adapter(Int4NumericRange, TypedNumericRangeAdapter)

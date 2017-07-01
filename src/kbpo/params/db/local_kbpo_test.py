# File wide connection.
"""
Database connection parameters for kbpo database
"""
from psycopg2.extras import NamedTupleCursor
_PARAMS = {
    'dbname':'kbpo_test',
    'user':'kbpo',
    'password':'kbpo',
    'host':'localhost',
    'port': 5432,
    'cursor_factory': NamedTupleCursor,
    'application_name': 'kbpo_test'
    }

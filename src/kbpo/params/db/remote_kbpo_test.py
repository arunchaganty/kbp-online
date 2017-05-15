# File wide connection.
"""
Database connection parameters for kbpo_test database
"""
from psycopg2.extras import NamedTupleCursor
_PARAMS = {
    'dbname':'kbpo_test',
    'user':'kbpo',
    'password':'kbpo',
    'host':'localhost',
    'port': 5433,
    'cursor_factory': NamedTupleCursor,
    }

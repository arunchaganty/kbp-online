# File wide connection.
"""
Database connection parameters for kbpo database
"""
from psycopg2.extras import NamedTupleCursor
_PARAMS = {
    'dbname':'kbp',
    'user':'kbp',
    'host':'localhost',
    'port': 4242,
    'cursor_factory': NamedTupleCursor,
    }

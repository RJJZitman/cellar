from typing import Dict, Optional, Any, List, Tuple, Union

import mysql.connector
from mysql.connector import Error
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class MariaDB:
    def __init__(self) -> None:
        pass

    def __enter__(self):
        self.initiate_connection()

    def __exit__(self, *exc_info):
        self.close_connection()

    def initiate_connection(self):
        pass

    def close_connection(self):
        pass

    def execute_query(self, query: str):
        pass

    def execute_query_select(self, query: str):
        pass

    def engine_connect(self):
        pass



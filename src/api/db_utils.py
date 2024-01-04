from typing import Optional, Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection
from mysql.connector.cursor import MySQLCursor


class MariaDB:
    """
    DB connector class for a JDBC connection to a MariaDB service.
    """
    def __init__(self, user: str, password: str, database: str, host: str = 'localhost', port: int = 3306) -> None:
        """
        Sets class attributes for further use.

        :param user: JDBC username
        :param password: JDBC password
        :param database: DB schema
        :param host: Hostname of the DB
        :param port: Port over which the connection is made
        """
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.connection: Optional[Connection] = None
        self.cursor: Optional[MySQLCursor] = None

        self.connection_string = f"mysql+mysqlconnector://" \
                                 f"{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def __enter__(self):
        """
        Context manager to initiate the DB connection.
        """
        self._initiate_connection()
        return self

    def __exit__(self, *exc_info):
        """
        Context manager to close the DB connection.
        """
        self._close_connection()

    def _initiate_connection(self):
        """
        Connects to the DB engine and initiates a cursor.
        """
        # Use SQLAlchemy to create a connection to MariaDB
        engine = self.engine_connect()
        self.connection = engine.connect()
        self.cursor = self.connection.connection.cursor()

    def _close_connection(self):
        """
        Closes both the DB connection and the cursor.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def engine_connect(self) -> Engine:
        """
        Constructs a sqlalchemy engine to connect to the DB.
        """
        # Use SQLAlchemy to create a MariaDB engine
        engine = create_engine(self.connection_string)
        return engine

    def execute_queries(self, queries: str) -> None:
        """
        Executes multiple queries separated by a ";".

        :param queries: The queries formatted as string
        """
        for query in queries.split(';')[:-1]:
            print(query)
            self.execute_query(query=f"{query};")

    def execute_query(self, query: str) -> None:
        """
        Executes a single query. Uses a transaction to commit the executed query automatically.

        :param query: The query that is executed
        """
        try:
            with self.connection.begin() as trans:
                self.cursor.execute(operation=query)
        except Exception as e:
            print(f"Error executing query: {e}")
            raise Exception(str(e))

    def execute_query_select(self, query: str, get_fields: bool = False) -> Any:
        """
        Executes a select query.

        :param query: The executed select query
        :param get_fields: Denotes whether the field names should be retrieved
        :return: The data requested by the query
        """
        self.cursor.execute(operation=query)
        result = self.cursor.fetchall()
        if get_fields:
            cols = self.cursor.column_names
            result = [{col: value for col, value in zip(cols, row)} for row in result]
        return result

    def execute_sql_file(self, file_path: str, multi: bool = False) -> None:
        """
        Reads a SQL string from a file and executes the query. Note that this method only support non-select queries.

        :param file_path: path to where the query-containing file lives
        :param multi: Denotes if the file contains multiple queries or a single one
        """
        with open(file=file_path, mode='r') as sql_file:
            if multi:
                self.execute_queries(queries=sql_file.read())
            else:
                self.execute_query(query=sql_file.read())

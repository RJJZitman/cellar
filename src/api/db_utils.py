from typing import Optional, Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection#, DBAPICursor


class MariaDB:
    def __init__(self, user: str, password: str, database: str, host: str = 'localhost', port: int = 3306) -> None:
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.connection: Optional[Connection] = None
        self.cursor: Optional[Any] = None

        self.connection_string = f"mysql+mysqlconnector://" \
                                 f"{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def __enter__(self):
        self._initiate_connection()
        return self

    def __exit__(self, *exc_info):
        self._close_connection(commit=True)

    def _initiate_connection(self):
        # Use SQLAlchemy to create a connection to MariaDB
        engine = self.engine_connect()
        self.connection = engine.connect()
        self.cursor = self.connection.connection.cursor()

    def _close_connection(self, commit: bool = False):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            if commit:
                self.connection.commit()
            self.connection.close()

    def engine_connect(self) -> Engine:
        # Use SQLAlchemy to create a MariaDB engine
        engine = create_engine(self.connection_string)
        return engine

    def execute_queries(self, queries: str) -> None:
        for query in queries.split(';')[:-1]:
            print(query)
            self.execute_query(query=f"{query};")

    def execute_query(self, query: str) -> None:
        try:
            trans = self.connection.begin()
            self.cursor.execute(operation=query)
            trans.commit()
        except Exception as e:
            print(f"Error executing query: {e}")
            self.connection.rollback()

    def execute_query_select(self, query: str, get_fields: bool = False) -> Any:
        self.cursor.execute(operation=query)
        result = self.cursor.fetchall()
        if get_fields:
            cols = self.cursor.column_names
            result = [{col: value for col, value in zip(cols, row)} for row in result]
        return result

    def execute_sql_file(self, file_path: str, multi: bool = False) -> None:
        with open(file=file_path, mode='r') as sql_file:
            if multi:
                self.execute_queries(queries=sql_file.read())
            else:
                self.execute_query(query=sql_file.read())
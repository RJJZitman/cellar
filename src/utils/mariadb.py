from typing import Optional, Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection, DBAPICursor


class MariaDB:
    def __init__(self, user: str, password: str, database: str, host: str = 'localhost', port: int = 3306) -> None:
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.connection: Optional[Connection] = None
        self.cursor: Optional[DBAPICursor] = None

    def __enter__(self):
        self._initiate_connection()
        return self

    def __exit__(self, *exc_info):
        self._close_connection()

    def _initiate_connection(self):
        # Use SQLAlchemy to create a connection to MariaDB
        engine = self.engine_connect()
        self.connection = engine.connect()
        self.cursor = self.connection.connection.cursor()

    def _close_connection(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def engine_connect(self) -> Engine:
        # Use SQLAlchemy to create a MariaDB engine
        connection_string = f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        engine = create_engine(connection_string)
        return engine

    def execute_queries(self, queries: str) -> None:
        for query in queries.split(';')[:-1]:
            self.execute_query(query=f"{query};")

    def execute_query(self, query: str) -> None:
        try:
            self.cursor.execute(operation=query)
            self.connection.commit()
        except Exception as e:
            print(f"Error executing query: {e}")
            self.connection.rollback()

    def execute_query_select(self, query: str) -> Any:
        self.cursor.execute(operation=query)
        result = self.cursor.fetchall()
        return result

    def execute_sql_file(self, file_path: str, multi: bool = False) -> None:
        with open(file=file_path, mode='r') as sql_file:
            if multi:
                self.execute_queries(queries=sql_file.read())
            else:
                self.execute_query(query=sql_file.read())


if __name__ == "__main__":
    # Replace 'your_password' with the actual password for the 'Rogier' user
    with MariaDB(user='Rogier', password='your_password', database='') as db:
        print(db.execute_query_select("show databases;"))
        db.execute_query("drop database if exists cellar;")
        db.execute_sql_file(file_path='/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/src/sql/create_databases.sql')
        db.execute_sql_file(file_path='/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/src/sql/create_tables.sql',
                            multi=True)

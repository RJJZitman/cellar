import os
import time

from typing import Optional, Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection, DBAPICursor

from .models import DbConnModel


class MariaDB:
    def __init__(self, user: str, password: str, database: str, host: str = 'localhost', port: int = 3306) -> None:
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.connection: Optional[Connection] = None
        self.cursor: Optional[DBAPICursor] = None

        self.connection_string = f"mysql+mysqlconnector://" \
                                 f"{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

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
        engine = create_engine(self.connection_string)
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


def database_service() -> None:
    os.system('brew services restart mariadb')
    time.sleep(15)


def setup_new_database(db_conn: MariaDB) -> None:
    print(db_conn.execute_query_select("show databases;"))
    db_conn.execute_query("drop database if exists cellar;")
    print(db_conn.execute_query_select("show databases;"))
    db_conn.execute_sql_file(file_path='/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/src/sql/create_databases.sql')
    db_conn.execute_sql_file(file_path='/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/src/sql/create_tables.sql',
                             multi=True)
    print(db_conn.execute_query_select("show databases;"))


def check_for_cellar_db(db_conn: MariaDB) -> bool:
    existing_dbs = db_conn.execute_query_select("show databases")
    if sum([1 for existing_db in existing_dbs if existing_db[0] == "cellar"]):
        print("cellar DB has been found")
        return True
    else:
        return False


def check_for_admin_user(db_conn: MariaDB) -> bool:
    owners = db_conn.execute_query_select(query="SELECT * FROM cellar.owners")
    if owners:
        return True
    else:
        print("No wine owners are found, DB is being re-instantiated")
        return False


def db_setup(db_creds: DbConnModel) -> None:
    database_service()
    with MariaDB(**db_creds.model_dump()) as db:
        if not (check_for_cellar_db(db_conn=db) and check_for_admin_user(db_conn=db)):
            setup_new_database(db_conn=db)
